"""Local, payload-free traces and SDK callbacks; no model-internal reasoning."""

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from time import perf_counter
from uuid import uuid4

from langchain_core.callbacks import BaseCallbackHandler

TOOLS = {
    "add",
    "add_tool",
    "lookup_product_spec",
    "lookup_product_spec_tool",
    "search_knowledge_base",
}


def safe_name(value):
    text = str(value or "")
    if re.search(r"(?i)(bearer|sk-[a-z0-9]|password|secret|api_key|authorization)", text):
        return "redacted"
    return text if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.:-]{0,79}", text) else "redacted"


def correlation(value):
    return "ref-" + hashlib.sha256(str(value).encode()).hexdigest()[:20]


class Trace:
    def __init__(self, path=None, *, run_id=None, thread_id=None):
        self.run_id = run_id or uuid4().hex
        self.thread_id = thread_id
        self.path = Path(path) if path else None
        self.events = []
        self.lock = RLock()

    def emit(self, event_type, *, layer="application", **details):
        # Free text, prompts, arguments, outputs, headers and documents are never serialized.
        item = {
            "timestamp": datetime.now(UTC).isoformat(),
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "node_name": None,
            "model_round": None,
            "event_type": safe_name(event_type),
            "tool_call_id": None,
            "tool_name": None,
            "status": None,
            "elapsed_ms": None,
            "token_usage": None,
            "error_type": None,
            "layer": safe_name(layer),
            "timing_basis": "observed_now",
        }
        for key in ("node_name", "status", "error_type", "timing_basis"):
            if details.get(key) is not None:
                item[key] = safe_name(details[key])
        if details.get("tool_name"):
            name = details["tool_name"]
            item["tool_name"] = name if name in TOOLS else "unknown_tool"
        if details.get("tool_call_id") is not None:
            item["tool_call_id"] = correlation(details["tool_call_id"])
        if type(details.get("model_round")) is int:
            item["model_round"] = details["model_round"]
        elapsed = details.get("elapsed_ms")
        if type(elapsed) in (float, int) and 0 <= elapsed < float("inf"):
            item["elapsed_ms"] = round(elapsed, 3)
        usage = details.get("token_usage")
        if isinstance(usage, dict):
            counts = {
                k: usage[k]
                for k in ("input_tokens", "output_tokens", "total_tokens")
                if type(usage.get(k)) is int and usage[k] >= 0
            }
            if counts:
                item["token_usage"] = counts
        with self.lock:
            self.events.append(item)
            if self.path:
                with self.path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(item, allow_nan=False) + "\n")
        return item

    def import_event(self, event, *, layer="native", imported=False):
        name = event.get("event", "UNKNOWN")
        self.emit(
            name,
            layer=layer,
            node_name=event.get("node_name"),
            model_round=event.get("model_round"),
            tool_call_id=event.get("tool_call_id"),
            tool_name=event.get("tool_name"),
            status=event.get("execution_status", event.get("status")),
            elapsed_ms=event.get("elapsed_ms"),
            error_type=event.get("error_type"),
            token_usage=event.get("token_usage"),
            timing_basis="imported_observation" if imported else "callback",
        )


class TraceCallback(BaseCallbackHandler):
    """Observe actual framework model/tool/node callbacks without logging payloads."""

    def __init__(self, trace, layer="langchain"):
        self.trace, self.layer = trace, layer
        self.active = {}

    def _start(self, kind, run_id, name=None):
        self.active[str(run_id)] = (kind, name, perf_counter())
        self.trace.emit(
            kind + "_START",
            layer=self.layer,
            node_name=name if kind == "NODE" else None,
            tool_name=name if kind == "TOOL" else None,
            tool_call_id=run_id if kind == "TOOL" else None,
            timing_basis="callback",
        )

    def _end(self, run_id, error=None):
        record = self.active.pop(str(run_id), None)
        if record:
            kind, name, started = record
            self.trace.emit(
                kind + "_END",
                layer=self.layer,
                node_name=name if kind == "NODE" else None,
                tool_name=name if kind == "TOOL" else None,
                tool_call_id=run_id if kind == "TOOL" else None,
                status="failed" if error else "completed",
                error_type=type(error).__name__ if error else None,
                elapsed_ms=(perf_counter() - started) * 1000,
                timing_basis="callback",
            )

    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        self._start("MODEL", run_id)

    def on_llm_end(self, response, *, run_id, **kwargs):
        self._end(run_id)

    def on_llm_error(self, error, *, run_id, **kwargs):
        self._end(run_id, error)

    def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        self._start("TOOL", run_id, (serialized or {}).get("name"))

    def on_tool_end(self, output, *, run_id, **kwargs):
        self._end(run_id)

    def on_tool_error(self, error, *, run_id, **kwargs):
        self._end(run_id, error)

    def on_chain_start(self, serialized, inputs, *, run_id, metadata=None, **kwargs):
        node = (metadata or {}).get("langgraph_node")
        if node:
            self._start("NODE", run_id, node)

    def on_chain_end(self, outputs, *, run_id, **kwargs):
        self._end(run_id)

    def on_chain_error(self, error, *, run_id, **kwargs):
        self._end(run_id, error)


class ObservedGraph:
    """Forward graph operations; only augment invoke's existing callback configuration."""

    def __init__(self, graph, trace):
        self.graph, self.callback = graph, TraceCallback(trace, "langgraph")

    def __getattr__(self, name):
        return getattr(self.graph, name)

    def invoke(self, value, config=None):
        config = dict(config or {})
        config["callbacks"] = [*(config.get("callbacks") or []), self.callback]
        return self.graph.invoke(value, config)


def read_trace(path, run_id):
    with Path(path).open(encoding="utf-8") as stream:
        return [event for line in stream if (event := json.loads(line))["run_id"] == run_id]
