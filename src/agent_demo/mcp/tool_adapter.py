"""Thin async MCP -> LangChain Tool adapter; keep one live connection per run."""

import asyncio
import json
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import ToolMessage
from langchain_core.tools import StructuredTool, ToolException

from agent_demo.agents.langchain_agent import AgentAnswer
from agent_demo.mcp.client import MCPClientError, MCPConnection


async def discover_langchain_tools(connection):
    definitions = await connection.discover()
    tools = []
    for definition in definitions:
        # Capture per iteration; tools must not all invoke the last discovered name.
        def bind(name):
            async def invoke(**arguments):
                try:
                    result = await connection.call_tool(name, arguments)
                except MCPClientError as exc:
                    raise ToolException(exc.error_type) from None
                return json.dumps(result, allow_nan=False)

            return invoke

        tools.append(
            StructuredTool(
                name=definition.name,
                description=definition.description,
                args_schema=definition.input_schema,
                coroutine=bind(definition.name),
            )
        )
    return tools


@dataclass
class MCPAgentResult:
    status: str
    answer: AgentAnswer | None
    state: dict
    events: list[dict]
    server_info: dict
    error_type: str | None = None


async def run_mcp_agent(model, prompt, *, connection=None, timeout=30.0, recursion_limit=16):
    """Independent Phase 3-style create_agent entry, leaving direct tools untouched.

    recursion_limit guards graph steps, not an exact tool-call count. Timeout
    cancels waiting; the connection context then closes the owned child process.
    """
    if type(timeout) not in (float, int) or not 0 < timeout <= 300:
        raise ValueError("invalid task timeout")
    if type(recursion_limit) is not int or not 1 <= recursion_limit <= 100:
        raise ValueError("invalid recursion limit")
    connection = connection or MCPConnection()
    state = {}
    try:
        async with asyncio.timeout(timeout):
            async with connection:
                tools = await discover_langchain_tools(connection)
                agent = create_agent(
                    model=model,
                    tools=tools,
                    response_format=ToolStrategy(AgentAnswer),
                    system_prompt=(
                        "Use only granted MCP tools for arithmetic and MOCK specifications. "
                        "MOCK data is not real product evidence. Return the structured answer."
                    ),
                )
                state = await agent.ainvoke(
                    {"messages": [{"role": "user", "content": prompt}]},
                    {"recursion_limit": recursion_limit},
                )
                if any(
                    isinstance(message, ToolMessage) and message.status == "error"
                    for message in state.get("messages", [])
                ):
                    raise MCPClientError("tool_call_rejected")
                if any(event["status"] == "failed" for event in connection.events):
                    raise MCPClientError("mcp_tool_failed")
                answer = state.get("structured_response")
                if not isinstance(answer, AgentAnswer):
                    raise MCPClientError("missing_structured_output")
        return MCPAgentResult("completed", answer, state, connection.events, connection.info)
    except Exception as exc:
        error = exc.error_type if isinstance(exc, MCPClientError) else type(exc).__name__
        return MCPAgentResult(
            "timeout" if isinstance(exc, TimeoutError) else "failed",
            None,
            state,
            connection.events,
            connection.info,
            error,
        )
