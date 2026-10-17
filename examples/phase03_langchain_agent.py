"""Run the LangChain 1.x create_agent implementation."""

import argparse
import json

from agent_demo.agents.langchain_agent import run_langchain_agent
from agent_demo.config import load_model_settings, load_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="?", default="Query MOCK-SW-48 and calculate total ports.")
    parser.add_argument("--mock", action="store_true", help="Scripted offline model; no API Key")
    args = parser.parse_args()
    try:
        load_settings()
        if args.mock:
            from agent_demo.evaluation.fixtures import ScriptedChat, chat_call

            model = ScriptedChat(
                replies=[
                    chat_call("lookup_product_spec_tool", {"model": "MOCK-SW-48"}, "spec"),
                    chat_call("add_tool", {"a": 48, "b": 4}, "sum"),
                    chat_call(
                        "AgentAnswer",
                        {"model": "MOCK-SW-48", "conclusion": "MOCK only", "total_ports": 52},
                        "answer",
                    ),
                ]
            )
        else:
            from langchain_google_genai import ChatGoogleGenerativeAI

            settings = load_model_settings()
            model = ChatGoogleGenerativeAI(
                model=settings.model,
                api_key=settings.api_key,
                temperature=0,
                max_tokens=2048,
                max_retries=0,
            )
        result = run_langchain_agent(model, args.prompt)
        print(
            json.dumps(
                {
                    "status": result.status,
                    "execution_mode": "offline_mock" if args.mock else "real_llm",
                    "answer": result.answer.model_dump() if result.answer else None,
                    "error_type": result.error_type,
                    "elapsed_ms": result.elapsed_ms,
                },
                ensure_ascii=True,
            )
        )
        return 0 if result.status == "completed" else 1
    except Exception as error:
        print(json.dumps({"status": "configuration_error", "error_type": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
