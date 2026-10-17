"""Bounded official v2 Client; discovery never expands the application allowlist."""

import asyncio
import json
import math
import sys
from time import perf_counter
from uuid import uuid4

from mcp import Client, StdioServerParameters
from mcp.shared.exceptions import MCPError
from mcp.types import CONNECTION_CLOSED, REQUEST_TIMEOUT

from agent_demo.mcp.server import ALLOWED_TOOLS
from agent_demo.tools import finite_number, validate_arguments, validate_model


class MCPClientError(RuntimeError):
    def __init__(self, error_type, *, protocol_code=None):
        super().__init__(error_type)
        self.error_type = error_type
        self.protocol_code = protocol_code


def local_server():
    """Application-owned command; neither prompts nor tools choose the executable."""
    return StdioServerParameters(
        command=sys.executable, args=["-m", "agent_demo.mcp.server"], env={"PYTHONUNBUFFERED": "1"}
    )


def _failure(exc, *, connecting=False):
    if isinstance(exc, TimeoutError) or (isinstance(exc, MCPError) and exc.code == REQUEST_TIMEOUT):
        return MCPClientError("timeout")
    if isinstance(exc, MCPError) and exc.code == CONNECTION_CLOSED:
        return MCPClientError("connection_failed" if connecting else "connection_lost")
    if isinstance(exc, MCPError):
        return MCPClientError("protocol_error", protocol_code=exc.code)
    return MCPClientError("connection_failed" if connecting else "connection_lost")


def parse_result(name, reply):
    """Validate the known business contract, not just the SDK's generic dict schema."""
    if reply.is_error:
        raise MCPClientError("tool_error")
    payload = reply.structured_content
    if payload is None:
        try:
            text = "".join(part.text for part in reply.content if part.type == "text")
            payload = json.loads(text)
        except (ValueError, TypeError, AttributeError):
            raise MCPClientError("invalid_response") from None
    try:
        if not isinstance(payload, dict) or set(payload) != {"status", "result"}:
            raise ValueError()
        if payload["status"] != "ok":
            raise ValueError()
        value = payload["result"]
        if name == "add":
            finite_number(value)
        elif name == "lookup_product_spec":
            if not isinstance(value, dict) or value.get("source_type") != "mock":
                raise ValueError()
            validate_model(value["model"])
            common = {"status", "model", "source_type"}
            if value["status"] == "not_found":
                if set(value) != common:
                    raise ValueError()
            elif value["status"] == "ok":
                ports = {"downlink_ports", "uplink_ports"}
                speeds = {"downlink_speed", "uplink_speed"}
                if set(value) != common | ports | speeds:
                    raise ValueError()
                if any(type(value[k]) is not int or value[k] < 0 for k in ports):
                    raise ValueError()
                if any(not isinstance(value[k], str) or not value[k].strip() for k in speeds):
                    raise ValueError()
            else:
                raise ValueError()
        else:
            raise ValueError()
    except (ValueError, TypeError, KeyError, OverflowError):
        raise MCPClientError("invalid_response") from None
    return payload


class MCPConnection:
    """Use inside one async task; SDK owns transport, handshake and process cleanup.

    A custom server is trusted application/test configuration, never model input.
    No automatic retries: a timeout does not prove the remote action was cancelled.
    """

    def __init__(
        self, server=None, *, timeout=10.0, connect_timeout=10.0, allowed_tools=ALLOWED_TOOLS
    ):
        for value in (timeout, connect_timeout):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError("timeouts must be finite and positive")
        self.allowed_tools = frozenset(allowed_tools)
        if not self.allowed_tools <= ALLOWED_TOOLS:
            raise ValueError("only approved business tools may be granted")
        self.sdk = Client(
            server if server is not None else local_server(), read_timeout_seconds=connect_timeout
        )
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.connected = False
        self.poisoned = False
        self.events = []
        self.run_id = uuid4().hex
        self.info = {}

    async def __aenter__(self):
        try:
            # The SDK auto-negotiation probe has its own defaults; bound the
            # entire connection attempt too. Cleanup may extend the wait.
            async with asyncio.timeout(self.connect_timeout):
                await self.sdk.__aenter__()
        except Exception as exc:
            raise _failure(exc, connecting=True) from None
        self.connected = True
        self.info = {
            "protocol_version": self.sdk.protocol_version,
            "server_info": self.sdk.server_info.model_dump() if self.sdk.server_info else None,
            "capabilities": self.sdk.server_capabilities.model_dump(exclude_none=True),
        }
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            # Close SDK task groups normally; the outer async-with still propagates
            # the caller's exception, without wrapping it into nested ExceptionGroups.
            await self.sdk.__aexit__(None, None, None)
        finally:
            self.connected = False

    def _check(self):
        if not self.connected or self.poisoned:
            raise MCPClientError("connection_unavailable")

    async def discover(self):
        self._check()
        try:
            result = await self.sdk.list_tools()
            tools = []
            seen = set()
            for item in result.tools:
                if item.name in seen:
                    raise MCPClientError("invalid_discovery")
                seen.add(item.name)
                if item.name not in self.allowed_tools:
                    continue
                if not item.description or item.input_schema.get("type") != "object":
                    raise MCPClientError("invalid_discovery")
                tools.append(item)
            if result.next_cursor is not None:
                raise MCPClientError("unexpected_pagination")
            return tools
        except MCPClientError:
            raise
        except Exception as exc:
            raise _failure(exc) from None

    async def call_tool(self, name, arguments):
        self._check()
        if name not in self.allowed_tools:
            raise MCPClientError("unauthorized_tool")
        try:
            validated = validate_arguments(name, arguments)
        except (ValueError, TypeError, OverflowError, RecursionError):
            raise MCPClientError("invalid_arguments") from None
        started = perf_counter()
        event = {"run_id": self.run_id, "tool_name": name, "arguments": validated}
        try:
            reply = await self.sdk.call_tool(name, validated, read_timeout_seconds=self.timeout)
            payload = parse_result(name, reply)
            if name == "lookup_product_spec" and payload["result"]["model"] != validated["model"]:
                raise MCPClientError("invalid_response")
            event["status"] = "completed"
            return payload
        except MCPClientError as exc:
            event.update(status="failed", error_type=exc.error_type)
            raise
        except Exception as exc:
            failure = _failure(exc)
            self.poisoned = True
            event.update(status="failed", error_type=failure.error_type)
            raise failure from None
        finally:
            event["elapsed_ms"] = round((perf_counter() - started) * 1000, 3)
            self.events.append(event)
