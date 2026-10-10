from time import sleep

from agent_demo.agents.agent_loop import LoopLimits, run_agent_loop
from agent_demo.agents.tool_calling import ModelReply, ToolCall


class Fake:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    def first(self, prompt, definitions):
        self.calls.append("first")
        return next(self.replies)

    def continue_turn(self, prompt, history, outputs, definitions):
        self.calls.append(("continue", len(history), outputs))
        return next(self.replies)


def test_direct_answer_and_multi_round_order():
    direct = run_agent_loop(Fake([ModelReply(text="hello")]), "hi")
    assert (direct.status, direct.answer) == ("completed", "hello")
    fake = Fake(
        [
            ModelReply(calls=(ToolCall("lookup_product_spec", {"model": "MOCK-SW-48"}, "a"),)),
            ModelReply(calls=(ToolCall("add", {"a": 48, "b": 4}, "b"),)),
            ModelReply(text="52"),
        ]
    )
    result = run_agent_loop(fake, "lookup then add")
    assert result.status == "completed" and result.answer == "52"
    assert [item[0] if isinstance(item, tuple) else item for item in fake.calls] == [
        "first",
        "continue",
        "continue",
    ]
    assert [e["tool_call_id"] for e in result.events if e["event"] == "ACTION"] == ["a", "b"]


def test_same_round_multiple_tools_and_call_budget():
    fake = Fake(
        [
            ModelReply(
                calls=(
                    ToolCall("add", {"a": 1, "b": 2}, "a"),
                    ToolCall("add", {"a": 3, "b": 4}, "b"),
                )
            ),
            ModelReply(text="done"),
        ]
    )
    result = run_agent_loop(fake, "two", LoopLimits(max_tool_calls=2))
    assert result.status == "completed"
    limited = Fake(
        [
            ModelReply(
                calls=(
                    ToolCall("add", {"a": 1, "b": 2}, "a"),
                    ToolCall("add", {"a": 3, "b": 4}, "b"),
                )
            ),
            ModelReply(text="bad"),
        ]
    )
    result = run_agent_loop(limited, "two", LoopLimits(max_tool_calls=1))
    assert (
        result.status == "budget_exceeded"
        and len([e for e in result.events if e["event"] == "ACTION"]) == 1
    )


def test_round_budget_and_tool_timeout():
    endless = Fake([ModelReply(calls=(ToolCall("add", {"a": 1, "b": 2}, "x"),))] * 3)
    result = run_agent_loop(endless, "loop", LoopLimits(max_model_rounds=2))
    assert result.status == "budget_exceeded" and result.termination_reason == "max_model_rounds"

    original = __import__("agent_demo.agents.agent_loop", fromlist=["dispatch"]).dispatch
    module = __import__("agent_demo.agents.agent_loop", fromlist=["dispatch"])
    module.dispatch = lambda *args, **kwargs: sleep(0.05) or {"status": "ok"}
    try:
        result = run_agent_loop(
            Fake([ModelReply(calls=(ToolCall("add", {"a": 1, "b": 2}, "x"),))]),
            "slow",
            LoopLimits(tool_timeout=0.001),
        )
        assert result.status == "timeout"
    finally:
        module.dispatch = original


def test_model_retry_and_failure_are_bounded():
    class Failing:
        def first(self, *args):
            raise RuntimeError("offline")

    result = run_agent_loop(Failing(), "fail", LoopLimits(max_retries=2))
    assert result.status == "failed"
    assert len([e for e in result.events if e["event"] == "MODEL_REQUEST"]) == 3
