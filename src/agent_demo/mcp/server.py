"""Two approved, read-only business tools served by the official MCP v2 SDK."""

import logging
import sys
from copy import deepcopy
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from agent_demo.tools import TOOL_DEFINITIONS, dispatch, validate_arguments

ALLOWED_TOOLS = frozenset({"add", "lookup_product_spec"})


class ValidatedMCPServer(MCPServer):
    """Reject raw arguments before SDK coercion or ignored extra properties."""

    async def call_tool(self, name, arguments, context=None):
        if name not in ALLOWED_TOOLS:
            raise ToolError("unknown_tool")
        try:
            arguments = validate_arguments(name, arguments)
        except (ValueError, TypeError, OverflowError, RecursionError):
            raise ToolError("invalid_arguments") from None
        return await super().call_tool(name, arguments, context)

    async def list_tools(self):
        tools = await super().list_tools()
        schemas = {item["name"]: item["parameters"] for item in TOOL_DEFINITIONS}
        tools = [tool for tool in tools if tool.name in ALLOWED_TOOLS]
        for tool in tools:
            tool.input_schema = deepcopy(schemas[tool.name])
        return tools


def create_server():
    server = ValidatedMCPServer(
        "AGENT-DEMO Phase 7",
        version="0.1.0",
        instructions="Read-only calculator and MOCK switch data; no real product evidence.",
    )
    annotations = ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
    )

    def execute(name, arguments):
        output = dispatch(name, arguments)
        if output["status"] != "ok":
            raise ToolError(output["error_type"])
        return output

    @server.tool(
        name="add",
        description=TOOL_DEFINITIONS[0]["description"],
        annotations=annotations,
        structured_output=True,
    )
    def add_mcp(a: float, b: float) -> dict[str, Any]:
        return execute("add", {"a": a, "b": b})

    @server.tool(
        name="lookup_product_spec",
        description=TOOL_DEFINITIONS[1]["description"],
        annotations=annotations,
        structured_output=True,
    )
    def lookup_mcp(model: str) -> dict[str, Any]:
        return execute("lookup_product_spec", {"model": model})

    return server


def main():
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    logging.getLogger(__name__).warning("Phase 7 MCP stdio server starting; data is MOCK")
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
