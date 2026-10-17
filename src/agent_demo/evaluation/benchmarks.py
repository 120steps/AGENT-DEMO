"""Matched scripted plans and measured transport samples, never model quality claims."""

import asyncio
import json
from statistics import mean
from time import perf_counter

from agent_demo.agents.langchain_agent import add_tool, run_langchain_agent
from agent_demo.evaluation.fixtures import ScriptedChat, chat_call
from agent_demo.evaluation.models import EvaluationCase
from agent_demo.evaluation.rag_benchmark import offline_benchmark
from agent_demo.evaluation.scenarios import tool_case
from agent_demo.mcp.client import MCPConnection
from agent_demo.mcp.tool_adapter import discover_langchain_tools
from agent_demo.observability import Trace, TraceCallback


def run_benchmarks():
    rows = []
    case = EvaluationCase(
        case_id="benchmark-native",
        category="tool",
        description="TEST plan",
        input={"scenario": "multi"},
        expected_status="completed",
        data_source="MOCK-v1",
        execution_mode="offline_mock",
    )
    model_replies = [
        chat_call("lookup_product_spec_tool", {"model": "MOCK-SW-48"}, "spec"),
        chat_call("add_tool", {"a": 48, "b": 4}, "add"),
        chat_call(
            "AgentAnswer",
            {"model": "MOCK-SW-48", "conclusion": "TEST only", "total_ports": 52},
            "final",
        ),
    ]
    for sample in range(3):
        trace = Trace()
        started = perf_counter()
        native = tool_case(case, trace, None)
        native_ms = (perf_counter() - started) * 1000
        started = perf_counter()
        framework = run_langchain_agent(
            ScriptedChat(replies=model_replies, callbacks=[TraceCallback(trace)]),
            "MOCK query and calculate",
        )
        framework_ms = (perf_counter() - started) * 1000
        assert native.facts["tool_results"][-1] == 52
        assert framework.answer is not None and framework.answer.total_ports == 52
        rows.append(
            {
                "sample": sample,
                "native_ms": native_ms,
                "langchain_ms": framework_ms,
                "result": 52,
                "native_status": native.status,
                "langchain_status": framework.status,
            }
        )

    async def transport():
        samples = []
        started = perf_counter()
        async with MCPConnection() as connection:
            startup_ms = (perf_counter() - started) * 1000
            tools = {t.name: t for t in await discover_langchain_tools(connection)}
            for sample in range(3):
                started = perf_counter()
                direct = add_tool.invoke({"a": 15, "b": 27})
                python_ms = (perf_counter() - started) * 1000
                started = perf_counter()
                remote = json.loads(await tools["add"].ainvoke({"a": 15, "b": 27}))
                mcp_ms = (perf_counter() - started) * 1000
                assert direct == remote["result"] == 42
                samples.append(
                    {"sample": sample, "python_tool_ms": python_ms, "mcp_tool_ms": mcp_ms}
                )
        return {
            "startup_ms": startup_ms,
            "samples": samples,
            "python_mean_ms": mean(s["python_tool_ms"] for s in samples),
            "mcp_mean_ms": mean(s["mcp_tool_ms"] for s in samples),
        }

    return {
        "native_vs_langchain": {"mode": "scripted_framework_overhead", "samples": rows},
        "fixed_vs_agentic": offline_benchmark(),
        "python_vs_mcp": asyncio.run(transport()),
        "limits": "3 local samples, sequential warm calls, MCP startup separate; no real LLM. "
        "Different framework prompt/protocol shapes; "
        "cannot rank model quality or general performance.",
    }
