"""Scripted offline model or explicit live Gemini, both using real MCP stdio."""

import argparse
import asyncio
import json

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from agent_demo.config import load_model_settings
from agent_demo.mcp.tool_adapter import run_mcp_agent


class ScriptedMCPModel(BaseChatModel):
    """Fixed teaching transcript; never presented as an actual LLM decision."""

    index: int = 0

    @property
    def _llm_type(self):
        return "phase07-scripted-offline"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        calls = [
            ("lookup_product_spec", {"model": "MOCK-SW-48"}),
            ("add", {"a": 48, "b": 4}),
            (
                "AgentAnswer",
                {"model": "MOCK-SW-48", "total_ports": 52, "conclusion": "MOCK: 52 total ports."},
            ),
        ]
        name, arguments = calls[self.index]
        self.index += 1
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[
                            {"id": f"phase07-{self.index}", "name": name, "args": arguments}
                        ],
                    )
                )
            ]
        )


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Use explicitly configured Gemini")
    parser.add_argument("--prompt", default="Query MOCK-SW-48 and calculate the total port count.")
    args = parser.parse_args()
    try:
        if args.live:
            from langchain_google_genai import ChatGoogleGenerativeAI

            settings = load_model_settings()
            model = ChatGoogleGenerativeAI(
                model=settings.model,
                api_key=settings.api_key,
                temperature=0,
                max_retries=0,
                max_output_tokens=1024,
                timeout=15,
            )
        else:
            model = ScriptedMCPModel()
        result = await run_mcp_agent(model, args.prompt)
        print(
            json.dumps(
                {
                    "status": result.status,
                    "model_mode": "live_gemini" if args.live else "scripted_offline",
                    "transport": "real_stdio",
                    "server": result.server_info,
                    "answer": result.answer.model_dump() if result.answer else None,
                    "events": result.events,
                    "error_type": result.error_type,
                },
                ensure_ascii=True,
            )
        )
        return 0 if result.status == "completed" else 1
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
