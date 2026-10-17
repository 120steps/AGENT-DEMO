"""Discover and call a real, separately running stdio subprocess (no model/API key)."""

import asyncio
import json

from agent_demo.mcp.client import MCPClientError, MCPConnection


async def main():
    connection = MCPConnection()
    try:
        async with connection:
            tools = await connection.discover()
            output = {
                "connection": connection.info,
                "tools": [tool.model_dump(exclude_none=True) for tool in tools],
                "add": await connection.call_tool("add", {"a": 15, "b": 27}),
                "spec": await connection.call_tool("lookup_product_spec", {"model": "MOCK-SW-48"}),
            }
        output["connection_closed"] = not connection.connected
        output["events"] = connection.events
        print(json.dumps(output, ensure_ascii=True))
        return 0
    except MCPClientError as exc:
        print(json.dumps({"status": "failed", "error_type": exc.error_type}))
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
