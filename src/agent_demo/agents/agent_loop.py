"""Small, bounded native Agent Loop built on the Phase 1 client protocol."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4

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

    def __post_init__(self):
        if self.max_model_rounds < 1 or self.max_tool_calls < 1 or self.max_retries < 0:
            raise ValueError("loop counts must be positive and retries nonnegative")
        if self.tool_timeout <= 0 or self.task_timeout <= 0:
            raise ValueError("timeouts must be positive")


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
    run_id = uuid4().hex
    started = perf_counter()
    events: list[dict] = []
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "estimated_cost": None,
        "cost_status": "unavailable",
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
        last_error = None
        for attempt in range(limits.max_retries + 1):
            record("MODEL_REQUEST", execution_status="started", retry_attempt=attempt)
            call_started = perf_counter()
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    reply = pool.submit(fn).result(
                        timeout=max(0.01, limits.task_timeout - elapsed())
                    )
                record(
                    "MODEL_RESPONSE",
                    execution_status="received",
                    elapsed_ms=round((perf_counter() - call_started) * 1000, 3),
                    model_version=getattr(reply, "model_version", None),
                    token_usage=getattr(reply, "usage", None),
                )
                incoming = getattr(reply, "usage", None) or {}
                for key in ("input_tokens", "output_tokens", "total_tokens"):
                    usage[key] += int(incoming.get(key, 0) or 0)
                return reply
            except FutureTimeout:
                record("ERROR", execution_status="timeout", error_type="model_timeout")
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
        round_no += 1
        if not history:
            reply = model_call(lambda: client.first(prompt, TOOL_DEFINITIONS))
        else:
            reply = model_call(
                lambda: client.continue_turn(prompt, history, outputs, TOOL_DEFINITIONS)
            )
        if isinstance(reply, tuple):
            reason = reply[1]
            return result("timeout" if reason == "timeout" else "failed", reason)
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
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(dispatch, call.name, call.arguments)
                try:
                    output = future.result(
                        timeout=min(limits.tool_timeout, max(0.01, limits.task_timeout - elapsed()))
                    )
                except FutureTimeout:
                    record(
                        "OBSERVATION",
                        tool_call_id=call.call_id,
                        tool_name=call.name,
                        execution_status="timeout",
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
