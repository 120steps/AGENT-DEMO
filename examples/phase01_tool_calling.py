"""Run one manual tool round. --mock uses a fixed script, never intent routing."""

import argparse
import json

from agent_demo.agents.tool_calling import ModelReply, ToolCall, run_tool_calling
from agent_demo.config import load_model_settings, load_settings


class ScriptedClient:
    """A deterministic calculator transcript; it does not interpret the prompt."""

    def first(self, prompt, definitions):
        return ModelReply(calls=(ToolCall("add", {"a": 15, "b": 27}, "mock-call-1"),))

    def finish(self, prompt, first, outputs, definitions):
        return ModelReply(text=f"MOCK transcript: 15 + 27 = {outputs[0]['result']}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="?", default="What is 15 + 27?")
    parser.add_argument(
        "--mock", action="store_true", help="Fixed offline transcript, not a real LLM"
    )
    args = parser.parse_args()
    client = None
    try:
        load_settings()  # Reuse Phase 0 application configuration validation.
        if args.mock:
            client = ScriptedClient()
        else:
            from agent_demo.integrations.gemini import GeminiClient

            client = GeminiClient(load_model_settings())
        result = run_tool_calling(
            client,
            args.prompt,
            event_sink=lambda entry: print(json.dumps(entry, ensure_ascii=False)),
        )
        print(json.dumps({"status": result.status, "answer": result.answer}, ensure_ascii=False))
        return 0 if result.status == "completed" else 1
    except Exception as error:
        print(json.dumps({"status": "configuration_error", "error_type": type(error).__name__}))
        return 1
    finally:
        if client and hasattr(client, "close"):
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
