"""Small, bounded native Agent Loop built on the Phase 1 client protocol."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from time import perf_counter
from uuid import uuid4

from agent_demo.agents.execution import wait_until
from agent_demo.agents.tool_calling import ModelReply, ResponseFormatError, ToolCall
from agent_demo.tools import TOOL_DEFINITIONS, dispatch


@dataclass(frozen=True)
class LoopLimits:
    max_model_rounds: int = 6
    max_tool_calls: int = 12
    tool_timeout: float = 2.0
    task_timeout: float = 30.0
    max_retries: int = 1
    max_output_tokens: int = 2048
    estimated_input_tokens: int | None = None
    estimated_output_tokens: int | None = None
    max_total_tokens: int = 16000

    def __post_init__(self):
        for name in ("max_model_rounds", "max_tool_calls", "max_output_tokens", "max_total_tokens"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.max_retries) is not int or self.max_retries < 0:
            raise ValueError("max_retries must be a nonnegative integer")
        for value in (self.tool_timeout, self.task_timeout):
            if type(value) not in (int, float) or not isfinite(value) or value <= 0:
                raise ValueError("timeouts must be finite positive numbers")


@dataclass
class LoopResult:
    run_id: str
    status: str
    answer: str
    events: list[dict]
    usage: dict
    termination_reason: str


def run_agent_loop(client, prompt: str, limits: LoopLimits | None = None, event_sink=None):
    limits = limits or LoopLimits()
    if hasattr(client, "for_run"):
        client = client.for_run(
            max_output_tokens=limits.max_output_tokens, timeout=limits.task_timeout
        )
    run_id = uuid4().hex
    started = perf_counter()
    events: list[dict] = []
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "estimated_cost": None,
        "cost_status": "unavailable",
        "available": False,
        "pre_call_estimated_cost": None,
        "price_source": None,
    }
    history = []
    tool_count = 0
    round_no = 0

    def record(event, **details):
        item = {
            "run_id": run_id,
            "model_round": round_no,
            "event": event,
            "tool_call_id": None,
            "tool_name": None,
            "elapsed_ms": None,
            "execution_status": None,
            "termination_reason": None,
            **details,
        }
        events.append(item)
        if event_sink:
            event_sink(item)

    def elapsed():
        return perf_counter() - started

    def result(status, reason, answer=""):
        record("TERMINATION", execution_status=status, termination_reason=reason)
        return LoopResult(run_id, status, answer, events, usage, reason)

    if not isinstance(prompt, str) or not prompt.strip():
        return result("failed", "invalid_prompt")

    def model_call(fn):
        nonlocal round_no
        last_error = None
        for attempt in range(limits.max_retries + 1):
            if round_no >= limits.max_model_rounds:
                return None, "max_model_rounds"
            if elapsed() >= limits.task_timeout:
                return None, "timeout"
            round_no += 1
            record("MODEL_REQUEST", execution_status="started", retry_attempt=attempt)
            call_started = perf_counter()
            try:
                reply = wait_until(fn, started + limits.task_timeout)
                if not isinstance(reply, ModelReply) or not isinstance(reply.calls, tuple):
                    raise ResponseFormatError("invalid model response")
                if not isinstance(reply.text, str) or (not reply.text.strip() and not reply.calls):
                    raise ResponseFormatError("empty response")
                if any(
                    not isinstance(c, ToolCall)
                    or not isinstance(c.name, str)
                    or not c.name
                    or (c.call_id is not None and (not isinstance(c.call_id, str) or not c.call_id))
                    for c in reply.calls
                ):
                    raise ResponseFormatError("invalid tool call")
                ids = [c.call_id for c in reply.calls if c.call_id is not None]
                if len(ids) != len(set(ids)):
                    raise ResponseFormatError("duplicate call IDs")
                record(
                    "MODEL_RESPONSE",
                    execution_status="received",
                    elapsed_ms=round((perf_counter() - call_started) * 1000, 3),
                    model_version=getattr(reply, "model_version", None),
                    token_usage=getattr(reply, "usage", None),
                )
                incoming = getattr(reply, "usage", None) or {}
                usage["available"] = usage["available"] or bool(incoming)
                for key in ("input_tokens", "output_tokens", "total_tokens"):
                    value = incoming.get(key, 0)
                    if type(value) is int and value >= 0:
                        usage[key] += value
                if usage["total_tokens"] >= limits.max_total_tokens:
                    return None, "max_total_tokens"
                return reply
            except TimeoutError:
                record(
                    "ERROR",
                    execution_status="timeout",
                    error_type="model_timeout",
                    cancellation_confirmed=False,
                )
                return None, "timeout"
            except Exception as error:
                last_error = error
                record(
                    "ERROR",
                    execution_status="retryable" if attempt < limits.max_retries else "failed",
                    error_type=type(error).__name__,
                )
        return None, type(last_error).__name__ if last_error else "model_error"

    while True:
        if elapsed() >= limits.task_timeout:
            return result("timeout", "task_timeout")
        if round_no >= limits.max_model_rounds:
            return result("budget_exceeded", "max_model_rounds")
        if not history:
            reply = model_call(lambda: client.first(prompt, TOOL_DEFINITIONS))
        else:
            reply = model_call(
                lambda: client.continue_turn(prompt, history, outputs, TOOL_DEFINITIONS)
            )
        if isinstance(reply, tuple):
            reason = reply[1]
            status = "budget_exceeded" if reason.startswith("max_") else "failed"
            return result("timeout" if reason == "timeout" else status, reason)
        if reply is None:
            return result("failed", "model_error")
        history.append(reply)
        if not reply.calls:
            record("FINAL_RESPONSE", execution_status="direct_answer", answer=reply.text)
            return result("completed", "model_finished", reply.text)
        outputs = []
        for call in reply.calls:
            if tool_count >= limits.max_tool_calls:
                return result("budget_exceeded", "max_tool_calls")
            tool_count += 1
            record(
                "ACTION",
                tool_call_id=call.call_id,
                tool_name=call.name,
                execution_status="requested",
            )
            tool_started = perf_counter()
            try:
                output = wait_until(
                    lambda call=call: dispatch(call.name, call.arguments),
                    min(tool_started + limits.tool_timeout, started + limits.task_timeout),
                )
            except TimeoutError:
                record(
                    "OBSERVATION",
                    tool_call_id=call.call_id,
                    tool_name=call.name,
                    execution_status="timeout",
                    cancellation_confirmed=False,
                    elapsed_ms=round((perf_counter() - tool_started) * 1000, 3),
                    error_type="tool_timeout",
                )
                return result("timeout", "tool_timeout")
            outputs.append(output)
            record(
                "OBSERVATION",
                tool_call_id=call.call_id,
                tool_name=call.name,
                execution_status=output["status"],
                elapsed_ms=round((perf_counter() - tool_started) * 1000, 3),
                result=output,
            )
        history[-1] = (reply, outputs)
