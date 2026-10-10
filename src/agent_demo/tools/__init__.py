"""Local tools, explicit schemas, and a manually controlled dispatcher."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from time import perf_counter


def finite_number(value: object) -> float:
    """Reject booleans, coercion from strings, NaN, infinity, and huge integers."""
    if type(value) not in (int, float):
        raise ValueError("Expected a finite number, excluding bool")
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError("Number is outside the finite float range") from error
    if not math.isfinite(result):
        raise ValueError("Expected a finite number")
    return result


def add(a: float, b: float) -> float:
    """Add two finite numbers; refuse nonfinite results as well."""
    return finite_number(finite_number(a) + finite_number(b))


def validate_model(model: object) -> str:
    if not isinstance(model, str) or not re.fullmatch(r"MOCK-SW-[0-9]{1,3}", model):
        raise ValueError("Expected a MOCK-SW-<number> model identifier")
    return model


def lookup_product_spec(model: str) -> dict:
    """Return explicitly simulated specifications; never read files or use a network."""
    model = validate_model(model)
    ports = {"MOCK-SW-24": 24, "MOCK-SW-48": 48}
    if model not in ports:
        return {"status": "not_found", "model": model, "source_type": "mock"}
    return {
        "status": "ok",
        "model": model,
        "downlink_ports": ports[model],
        "downlink_speed": "1 Gbps",
        "uplink_ports": 4,
        "uplink_speed": "10 Gbps",
        "source_type": "mock",
    }


TOOL_DEFINITIONS = [
    {
        "name": "add",
        "description": "Add two finite numbers using the local calculator.",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
            "additionalProperties": False,
        },
    },
    {
        "name": "lookup_product_spec",
        "description": "Look up MOCK switch specs. Simulated data, never real hardware.",
        "parameters": {
            "type": "object",
            "properties": {"model": {"type": "string", "pattern": "^MOCK-SW-[0-9]{1,3}$"}},
            "required": ["model"],
            "additionalProperties": False,
        },
    },
]

# A fixed application-owned allowlist; names never resolve to globals or imports.
TOOL_REGISTRY = {"add": add, "lookup_product_spec": lookup_product_spec}


def _json_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("Duplicate JSON key")
        result[name] = value
    return result


def _reject_constant(value):
    raise ValueError("Non-standard JSON constant")


def validate_arguments(name: str, arguments: object) -> dict:
    if isinstance(arguments, str):
        arguments = json.loads(
            arguments, parse_constant=_reject_constant, object_pairs_hook=_json_object
        )
    if not isinstance(arguments, dict):
        raise ValueError("Expected a JSON object")
    expected = {"a", "b"} if name == "add" else {"model"}
    if set(arguments) != expected:
        raise ValueError("Missing or unexpected parameter")
    if name == "add":
        return {key: finite_number(arguments[key]) for key in ("a", "b")}
    return {"model": validate_model(arguments["model"])}


def dispatch(name: str, arguments: object, emit: Callable[..., None] | None = None) -> dict:
    """Validate before execution; exceptions return types only, never secret-bearing text."""
    emit = emit or (lambda *args, **kwargs: None)
    started = perf_counter()
    if name not in TOOL_REGISTRY:
        emit("VALIDATION", execution_status="rejected", error_type="unknown_tool")
        return {"status": "error", "error_type": "unknown_tool"}
    try:
        validated = validate_arguments(name, arguments)
    except (ValueError, TypeError, OverflowError, RecursionError):
        emit("VALIDATION", execution_status="rejected", error_type="invalid_arguments")
        return {"status": "error", "error_type": "invalid_arguments"}
    emit("VALIDATION", validated_arguments=validated, execution_status="accepted")
    try:
        result = TOOL_REGISTRY[name](**validated)
    except Exception as error:
        emit(
            "TOOL_EXECUTION",
            validated_arguments=validated,
            execution_status="failed",
            elapsed_ms=round((perf_counter() - started) * 1000, 3),
            error_type=type(error).__name__,
        )
        return {"status": "error", "error_type": "tool_execution_failed"}
    emit(
        "TOOL_EXECUTION",
        validated_arguments=validated,
        execution_status="completed",
        elapsed_ms=round((perf_counter() - started) * 1000, 3),
    )
    return {"status": "ok", "result": result}
