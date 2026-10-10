"""Run a bounded multi-round native Agent Loop."""

import argparse
import json

from agent_demo.agents.agent_loop import LoopLimits, run_agent_loop
from agent_demo.agents.tool_calling import ModelReply, ToolCall
from agent_demo.config import load_model_settings, load_settings


class ScriptedClient:
    def __init__(self):
        self.round = 0

    def first(self, prompt, definitions):
        self.round += 1
        return ModelReply(
            calls=(ToolCall("lookup_product_spec", {"model": "MOCK-SW-48"}, "spec-1"),)
        )

    def continue_turn(self, prompt, history, outputs, definitions):
        self.round += 1
        if self.round == 2:
            return ModelReply(
                calls=(
                    ToolCall("add", {"a": outputs[0]["result"]["downlink_ports"], "b": 4}, "sum-2"),
                )
            )
        return ModelReply(
            text="MOCK-SW-48 has 48 downlink ports; adding 4 uplinks gives 52 total ports."
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "prompt", nargs="?", default="Look up MOCK-SW-48 and calculate total ports."
    )
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()
    client = None
    try:
        load_settings()
        if args.mock:
            client = ScriptedClient()
        else:
            from agent_demo.integrations.gemini import GeminiClient

            client = GeminiClient(load_model_settings())
        result = run_agent_loop(
            client,
            args.prompt,
            LoopLimits(),
            event_sink=lambda event: print(json.dumps(event, ensure_ascii=False)),
        )
        print(
            json.dumps(
                {
                    "status": result.status,
                    "termination_reason": result.termination_reason,
                    "answer": result.answer,
                    "usage": result.usage,
                },
                ensure_ascii=False,
            )
        )
        return 0 if result.status == "completed" else 1
    except Exception as error:
        print(json.dumps({"status": "configuration_error", "error_type": type(error).__name__}))
        return 1
    finally:
        if client and hasattr(client, "close"):
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
