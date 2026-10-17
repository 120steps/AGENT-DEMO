"""Separate in-memory SDK, real stdio, and scripted-model/real-MCP validation."""

import asyncio
import json
import subprocess
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from mcp import Client, StdioServerParameters
from mcp.client import stdio
from mcp.server import MCPServer
from mcp.types import CallToolResult, TextContent
from pydantic import Field

from agent_demo.agents.langchain_agent import add_tool, lookup_product_spec_tool
from agent_demo.mcp.client import MCPClientError, MCPConnection, local_server, parse_result
from agent_demo.mcp.server import ALLOWED_TOOLS, create_server
from agent_demo.mcp.tool_adapter import discover_langchain_tools, run_mcp_agent
from agent_demo.tools import TOOL_DEFINITIONS, TOOL_REGISTRY, dispatch, lookup_product_spec

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def child_processes(monkeypatch):
    """Observe real SDK spawn handles; assert reaped returncodes, never os.kill(pid, 0)."""
    children = []
    original = stdio._create_platform_compatible_process

    async def capture(*args, **kwargs):
        process = await original(*args, **kwargs)
        children.append(process)
        return process

    monkeypatch.setattr(stdio, "_create_platform_compatible_process", capture)
    yield children
    assert all(process.returncode is not None for process in children), "unreaped MCP child"


def fault_server(tmp_path, behavior):
    """Real isolated subprocess, with test-only faults unavailable in production server."""
    script = tmp_path / "fault_server.py"
    script.write_text(
        "import asyncio, os\n"
        "from mcp.server import MCPServer\n"
        "from mcp.server.mcpserver.exceptions import ToolError\n"
        "from mcp.shared.exceptions import MCPError\n"
        "server=MCPServer('fault-fixture')\n"
        "@server.tool(description='Fault injection test calculator')\n"
        "async def add(a:float,b:float)->dict:\n"
        f"    {behavior}\n"
        "server.run(transport='stdio')\n",
        encoding="utf-8",
    )
    return StdioServerParameters(command=sys.executable, args=[str(script)])


def tool_call(name, arguments, call_id="call-1"):
    return AIMessage(content="", tool_calls=[{"id": call_id, "name": name, "args": arguments}])


def final_answer():
    return tool_call(
        "AgentAnswer",
        {"model": "MOCK-SW-48", "conclusion": "MOCK: 52 ports", "total_ports": 52},
        "answer-1",
    )


class ScriptedModel(BaseChatModel):
    responses: list[Any]
    seen: list = Field(default_factory=list)
    index: int = 0

    @property
    def _llm_type(self):
        return "phase07-offline-test"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        reply = self.responses[self.index]
        self.index += 1
        return ChatResult(generations=[ChatGeneration(message=reply)])


def test_sdk_memory_discovery_and_business_reuse():
    async def scenario():
        before = deepcopy(lookup_product_spec("MOCK-SW-48"))
        async with Client(create_server()) as client:
            discovered = await client.list_tools()
            assert {t.name for t in discovered.tools} == ALLOWED_TOOLS
            for item in discovered.tools:
                expected = next(d for d in TOOL_DEFINITIONS if d["name"] == item.name)
                assert item.input_schema == expected["parameters"]
                assert item.description and item.annotations.read_only_hint
            result = await client.call_tool("add", {"a": 15, "b": 27})
            assert result.structured_content == {"status": "ok", "result": 42}
            spec = await client.call_tool("lookup_product_spec", {"model": "MOCK-SW-48"})
            assert spec.structured_content["result"] == before
            assert (await client.list_resources()).resources == []
            assert (await client.list_prompts()).prompts == []
        assert lookup_product_spec("MOCK-SW-48") == before

    asyncio.run(scenario())


def test_real_stdio_discovery_calls_and_process_exit(child_processes):
    async def scenario():
        conn = MCPConnection()
        async with conn:
            assert len(child_processes) == 1
            assert child_processes[0].returncode is None
            assert conn.info["protocol_version"]
            assert conn.info["server_info"]["name"] == "AGENT-DEMO Phase 7"
            assert {t.name for t in await conn.discover()} == ALLOWED_TOOLS
            assert (await conn.call_tool("add", {"a": 15, "b": 27}))["result"] == 42
            spec = (await conn.call_tool("lookup_product_spec", {"model": "MOCK-SW-48"}))["result"]
            assert spec["source_type"] == "mock" and spec["downlink_ports"] == 48
        assert not conn.connected
        with pytest.raises(MCPClientError, match="connection_unavailable"):
            await conn.call_tool("add", {"a": 1, "b": 2})

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("unknown", {}),
        ("add", {"a": 1}),
        ("add", {"a": True, "b": 2}),
        ("add", {"a": "1", "b": 2}),
        ("add", {"a": [], "b": 2}),
        ("add", {"a": 1, "b": 2, "path": "secret"}),
        ("lookup_product_spec", {"model": "../../secret"}),
        ("lookup_product_spec", {"model": "MOCK-SW-48", "command": "whoami"}),
    ],
)
def test_real_stdio_raw_sdk_cannot_bypass_server_validation(name, arguments, child_processes):
    async def scenario():
        async with Client(local_server()) as client:
            reply = await client.call_tool(name, arguments)
            assert reply.is_error
            assert reply.structured_content is None

    asyncio.run(scenario())


@pytest.mark.parametrize("value", [True, "15", float("inf"), float("nan"), 10**500])
def test_client_rejects_invalid_arguments_before_wire(value):
    async def scenario():
        async with MCPConnection(create_server()) as conn:
            with pytest.raises(MCPClientError, match="invalid_arguments"):
                await conn.call_tool("add", {"a": value, "b": 2})
            assert not conn.events

    asyncio.run(scenario())


def test_sdk_memory_business_execution_failure_uses_dispatcher(monkeypatch):
    def broken(a, b):
        raise RuntimeError("do not disclose private implementation details")

    monkeypatch.setitem(TOOL_REGISTRY, "add", broken)

    async def scenario():
        async with Client(create_server()) as client:
            reply = await client.call_tool("add", {"a": 1, "b": 2})
            assert reply.is_error
            text = str(reply.content)
            assert "tool_execution_failed" in text
            assert "private implementation" not in text

    asyncio.run(scenario())


def test_real_stdio_not_found_is_business_status(child_processes):
    async def scenario():
        async with MCPConnection() as conn:
            result = await conn.call_tool("lookup_product_spec", {"model": "MOCK-SW-99"})
            assert result["result"] == {
                "status": "not_found",
                "model": "MOCK-SW-99",
                "source_type": "mock",
            }

    asyncio.run(scenario())


def test_real_stdio_launch_failure():
    async def scenario():
        params = StdioServerParameters(command=str(ROOT / "nonexistent-python.exe"))
        with pytest.raises(MCPClientError, match="connection_failed"):
            async with MCPConnection(params, timeout=1):
                pytest.fail("must not connect")

    asyncio.run(scenario())


def test_real_stdio_exit_before_handshake(child_processes):
    async def scenario():
        params = StdioServerParameters(command=sys.executable, args=["-c", "raise SystemExit(3)"])
        with pytest.raises(MCPClientError):
            async with MCPConnection(params, timeout=1):
                pytest.fail("must not connect")

    asyncio.run(scenario())


def test_real_stdio_startup_timeout_reaps_unresponsive_child(child_processes):
    async def scenario():
        params = StdioServerParameters(
            command=sys.executable, args=["-c", "import time; time.sleep(30)"]
        )
        with pytest.raises(MCPClientError):
            async with MCPConnection(params, timeout=0.5, connect_timeout=0.5):
                pytest.fail("must not connect")

    started = time.monotonic()
    asyncio.run(scenario())
    assert time.monotonic() - started < 12


@pytest.mark.parametrize(
    "behavior,expected",
    [
        ("os._exit(17)", "connection_lost"),
        ("await asyncio.sleep(30); return {'status':'ok','result':42}", "timeout"),
        ("raise ToolError('controlled_failure')", "tool_error"),
        ("raise MCPError(-32602,'controlled_protocol_error')", "protocol_error"),
        ("return {'status':'ok','result':'42'}", "invalid_response"),
    ],
)
def test_real_stdio_faults_are_diagnostic_and_reaped(tmp_path, behavior, expected, child_processes):
    async def scenario():
        conn = MCPConnection(fault_server(tmp_path, behavior), timeout=1)
        async with conn:
            with pytest.raises(MCPClientError) as caught:
                await conn.call_tool("add", {"a": 15, "b": 27})
            assert caught.value.error_type == expected
            assert conn.events[-1]["status"] == "failed"
            if expected in {"timeout", "connection_lost"}:
                with pytest.raises(MCPClientError, match="connection_unavailable"):
                    await conn.call_tool("add", {"a": 1, "b": 2})

    started = time.monotonic()
    asyncio.run(scenario())
    assert time.monotonic() - started < 12


@pytest.mark.parametrize("payload", [None, {}, {"status": "ok", "result": True}, {"result": 42}])
def test_invalid_result_shape_is_not_success(payload):
    reply = CallToolResult(
        content=[TextContent(type="text", text="not json")], structured_content=payload
    )
    with pytest.raises(MCPClientError, match="invalid_response"):
        parse_result("add", reply)


def test_text_result_fallback():
    result = CallToolResult(content=[TextContent(type="text", text='{"status":"ok","result":42}')])
    assert parse_result("add", result)["result"] == 42


def test_discovery_filters_and_call_enforces_caller_grant():
    async def scenario():
        server = MCPServer("untrusted-discovery-fixture")

        @server.tool(name="add")
        def allowed_add(a: float, b: float) -> dict:
            """Allowed calculation using the existing dispatcher."""
            return dispatch("add", {"a": a, "b": b})

        @server.tool()
        def dangerous_tool() -> str:
            raise AssertionError("must never execute")

        async with MCPConnection(server, allowed_tools={"add"}) as conn:
            assert [t.name for t in await conn.discover()] == ["add"]
            with pytest.raises(MCPClientError, match="unauthorized_tool"):
                await conn.call_tool("lookup_product_spec", {"model": "MOCK-SW-48"})
            with pytest.raises(MCPClientError, match="unauthorized_tool"):
                await conn.call_tool("dangerous_tool", {})

    asyncio.run(scenario())


def test_real_stdio_adapter_preserves_names_schemas_and_calls(child_processes):
    async def scenario():
        async with MCPConnection() as conn:
            tools = {t.name: t for t in await discover_langchain_tools(conn)}
            assert set(tools) == ALLOWED_TOOLS
            assert tools["add"].args_schema == TOOL_DEFINITIONS[0]["parameters"]
            result = json.loads(await tools["add"].ainvoke({"a": 15, "b": 27}))
            assert result["result"] == 42
            spec = json.loads(await tools["lookup_product_spec"].ainvoke({"model": "MOCK-SW-48"}))
            assert spec["result"]["source_type"] == "mock"

    asyncio.run(scenario())


def test_scripted_agent_real_stdio_multi_step_id_order(child_processes):
    async def scenario():
        model = ScriptedModel(
            responses=[
                tool_call("lookup_product_spec", {"model": "MOCK-SW-48"}, "spec-1"),
                tool_call("add", {"a": 48, "b": 4}, "add-1"),
                final_answer(),
            ]
        )
        result = await run_mcp_agent(model, "MOCK query")
        assert result.status == "completed" and result.answer.total_ports == 52
        assert [e["tool_name"] for e in result.events] == ["lookup_product_spec", "add"]
        observed = [m for m in model.seen[2] if isinstance(m, ToolMessage)]
        assert [m.tool_call_id for m in observed] == ["spec-1", "add-1"]
        assert json.loads(observed[0].content)["result"]["source_type"] == "mock"
        assert json.loads(observed[1].content)["result"] == 52

    asyncio.run(scenario())


def test_scripted_agent_unknown_tool_does_not_execute(child_processes):
    async def scenario():
        model = ScriptedModel(
            responses=[tool_call("execute_command", {"command": "whoami"}), final_answer()]
        )
        result = await run_mcp_agent(model, "MOCK malicious request")
        assert result.status == "failed" and not result.events
        assert result.error_type == "tool_call_rejected"
        assert result.answer is None
        rejected = [m for m in model.seen[1] if isinstance(m, ToolMessage)]
        assert rejected[0].status == "error"

    asyncio.run(scenario())


def test_agent_mcp_failure_is_not_success(tmp_path, child_processes):
    async def scenario():
        conn = MCPConnection(fault_server(tmp_path, "raise ToolError('failure')"))
        model = ScriptedModel(responses=[tool_call("add", {"a": 15, "b": 27})])
        result = await run_mcp_agent(model, "MOCK task", connection=conn)
        assert result.status == "failed" and result.answer is None
        assert result.events[0]["error_type"] == "tool_error"

    asyncio.run(scenario())


def test_agent_total_timeout_closes_child(tmp_path, child_processes):
    async def scenario():
        conn = MCPConnection(fault_server(tmp_path, "await asyncio.sleep(30); return {}"))
        model = ScriptedModel(responses=[tool_call("add", {"a": 1, "b": 2})])
        result = await run_mcp_agent(model, "MOCK task", connection=conn, timeout=1)
        assert result.status == "timeout" and result.answer is None
        assert not conn.connected

    asyncio.run(scenario())


def test_phase03_direct_tools_still_work():
    assert add_tool.invoke({"a": 15, "b": 27}) == 42
    assert lookup_product_spec_tool.invoke({"model": "MOCK-SW-48"})["source_type"] == "mock"


def test_wrong_response_model_rejected():
    server = MCPServer("wrong-model-fixture")

    @server.tool(name="lookup_product_spec")
    def wrong_model(model: str) -> dict:
        return {"status": "ok", "result": lookup_product_spec("MOCK-SW-24")}

    async def scenario():
        async with MCPConnection(server) as conn:
            with pytest.raises(MCPClientError, match="invalid_response"):
                await conn.call_tool("lookup_product_spec", {"model": "MOCK-SW-48"})

    asyncio.run(scenario())


def test_context_closes_without_masking_caller_error(child_processes):
    async def scenario():
        with pytest.raises(MCPClientError, match="unauthorized_tool"):
            async with MCPConnection() as conn:
                await conn.call_tool("read_file", {"path": "secret"})

    asyncio.run(scenario())


def test_cli_stdout_is_json_and_stderr_owns_logs():
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples/phase07_mcp_client.py")],
        capture_output=True,
        text=True,
        timeout=20,
        cwd=ROOT,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["connection_closed"]
    assert payload["add"]["result"] == 42
    assert "MCP stdio server starting" in result.stderr


@pytest.mark.parametrize("timeout", [0, -1, True, float("nan"), float("inf")])
@pytest.mark.parametrize("field", ["timeout", "connect_timeout"])
def test_invalid_connection_deadline_rejected(timeout, field):
    with pytest.raises(ValueError):
        MCPConnection(**{field: timeout})
