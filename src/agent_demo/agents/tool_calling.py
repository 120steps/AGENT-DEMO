"""Exactly one tool round and at most two model requests; no Agent Loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from uuid import uuid4

from agent_demo.tools import TOOL_DEFINITIONS, dispatch


class ResponseFormatError(ValueError):
    """The model did not return a complete, supported response."""


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: object
    call_id: str | None = None


@dataclass(frozen=True)
class ModelReply:
    text: str = ""
    calls: tuple[ToolCall, ...] = ()
    context: object = field(default=None, repr=False)
    model_version: str | None = None


@dataclass
class RunResult:
    run_id: str
    status: str
    answer: str
    events: list[dict]


def run_tool_calling(client, prompt: str, event_sink=None) -> RunResult:
    """The client owns provider protocol; this function alone dispatches local tools."""
    run_id = uuid4().hex
    events = []

    def record(event, **details):
        entry = {
            "run_id": run_id,
            "event": event,
            "tool_call_id": None,
            "tool_name": None,
            "validated_arguments": None,
            "execution_status": None,
            "elapsed_ms": None,
            "error_type": None,
            **details,
        }
        events.append(entry)
        if event_sink:
            event_sink(entry)

    def request(operation):
        record("MODEL_REQUEST", execution_status="started")
        started = perf_counter()
        reply = operation()
        if (
            not isinstance(reply, ModelReply)
            or not isinstance(reply.text, str)
            or not isinstance(reply.calls, tuple)
            or (not reply.text.strip() and not reply.calls)
        ):
            raise ResponseFormatError("No text or tool calls")
        for call in reply.calls:
            if (
                not isinstance(call, ToolCall)
                or not isinstance(call.name, str)
                or not call.name
                or (
                    call.call_id is not None
                    and (not isinstance(call.call_id, str) or not call.call_id)
                )
            ):
                raise ResponseFormatError("Invalid tool name or call ID")
        ids = [call.call_id for call in reply.calls if call.call_id is not None]
        if len(ids) != len(set(ids)) or len(reply.calls) > 4:
            raise ResponseFormatError("Invalid call correlation or excessive calls")
        record(
            "MODEL_RESPONSE",
            execution_status="received",
            elapsed_ms=round((perf_counter() - started) * 1000, 3),
            model_version=reply.model_version,
        )
        return reply

    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 4000:
        record("ERROR", error_type="invalid_prompt", execution_status="rejected")
        return RunResult(run_id, "invalid_prompt", "", events)
    try:
        first = request(lambda: client.first(prompt, TOOL_DEFINITIONS))
        if not first.calls:
            record("FINAL_RESPONSE", execution_status="direct_answer", answer=first.text)
            return RunResult(run_id, "completed", first.text, events)

        outputs = []
        for call in first.calls:
            correlation = {"tool_call_id": call.call_id, "tool_name": call.name}
            record("TOOL_CALL", **correlation, execution_status="requested")

            def tool_event(event, **details):
                record(event, **correlation, **details)

            output = dispatch(call.name, call.arguments, emit=tool_event)
            outputs.append(output)
            record("TOOL_RESULT", **correlation, execution_status=output["status"], result=output)

        final = request(lambda: client.finish(prompt, first, outputs, TOOL_DEFINITIONS))
        if final.calls:
            record("FINAL_RESPONSE", execution_status="additional_tool_call_required")
            return RunResult(run_id, "additional_tool_call_required", "", events)
        status = "tool_error" if any(item["status"] == "error" for item in outputs) else "completed"
        record("FINAL_RESPONSE", execution_status=status, answer=final.text)
        return RunResult(run_id, status, final.text, events)
    except Exception as error:
        # Do not log provider exception text, headers, or raw SDK responses.
        status = "response_error" if isinstance(error, ResponseFormatError) else "api_error"
        record("ERROR", execution_status=status, error_type=type(error).__name__)
        return RunResult(run_id, status, "", events)
