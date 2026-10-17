"""Historical control gaps: actual waits, schema boundaries and provider messages."""

from threading import Event
from time import perf_counter

import pytest
from google.genai import types
from langchain_core.messages import AIMessage, ToolMessage

from agent_demo.agents.agent_loop import LoopLimits, run_agent_loop
from agent_demo.agents.langchain_agent import add_tool, run_langchain_agent
from agent_demo.agents.tool_calling import ModelReply, ToolCall
from agent_demo.config import ModelSettings
from agent_demo.evaluation.fixtures import NativeScript, ScriptedChat, chat_call
from agent_demo.integrations.gemini import GeminiClient


def final(value=42):
    return chat_call(
        "AgentAnswer",
        {"model": "MOCK-SW-48", "conclusion": "MOCK only", "total_ports": value},
        "final",
    )


@pytest.mark.parametrize("field", ["max_output_tokens", "max_model_rounds", "max_total_tokens"])
@pytest.mark.parametrize("value", [0, True, float("nan")])
def test_invalid_limits_rejected(field, value):
    with pytest.raises(ValueError):
        LoopLimits(**{field: value})


def test_native_model_and_tool_wait_return_before_operation_finishes(monkeypatch):
    gate, started = Event(), Event()

    def slow(*args):
        started.set()
        gate.wait(3)
        return ModelReply(text="late")

    class Slow:
        first = staticmethod(slow)

    before = perf_counter()
    try:
        result = run_agent_loop(Slow(), "test", LoopLimits(task_timeout=0.04))
        assert started.is_set() and result.status == "timeout" and not result.answer
        assert perf_counter() - before < 1
        assert any(e.get("cancellation_confirmed") is False for e in result.events)
    finally:
        gate.set()


def test_native_model_budget_includes_retries_and_usage():
    result = run_agent_loop(
        NativeScript([ConnectionError("test")] * 5),
        "task",
        LoopLimits(max_model_rounds=2, max_retries=4),
    )
    assert result.status == "budget_exceeded"
    assert len([e for e in result.events if e["event"] == "MODEL_REQUEST"]) == 2
    result = run_agent_loop(
        NativeScript([ModelReply(text="must not succeed", usage={"total_tokens": 20})]),
        "task",
        LoopLimits(max_total_tokens=10),
    )
    assert result.status == "budget_exceeded" and not result.answer


def test_gemini_complete_history_has_one_result_per_call_and_config_propagates():
    captured = []

    class SDK:
        class models:
            @staticmethod
            def generate_content(**kwargs):
                captured.append(kwargs)
                return types.GenerateContentResponse(
                    candidates=[
                        types.Candidate(
                            content=types.Content(role="model", parts=[types.Part(text="done")]),
                            finish_reason=types.FinishReason.STOP,
                        )
                    ]
                )

    client = GeminiClient(ModelSettings("TEST-key"), SDK()).for_run(max_output_tokens=77, timeout=2)
    call = ToolCall("add", {"a": 15, "b": 27}, "a")
    reply = ModelReply(
        calls=(call,),
        context=types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(name="add", args=call.arguments, id="a")
                )
            ],
        ),
    )
    client.continue_turn(
        "task", [(reply, [{"status": "ok", "result": 42}])], [{"status": "ok", "result": 42}], []
    )
    parts = [p for c in captured[0]["contents"] for p in c.parts if p.function_response]
    assert len(parts) == 1 and parts[0].function_response.id == "a"
    assert captured[0]["config"].max_output_tokens == 77


@pytest.mark.parametrize("bad", [True, "1", float("inf"), float("nan")])
def test_framework_does_not_coerce_invalid_business_arguments(bad):
    with pytest.raises(ValueError):
        add_tool.invoke({"a": bad, "b": 2})


@pytest.mark.parametrize(
    "field,value,reason",
    [("max_tool_calls", 1, "max_tool_calls"), ("max_model_rounds", 1, "max_model_rounds")],
)
def test_framework_independent_budgets(field, value, reason):
    responses = [
        AIMessage(
            content="",
            tool_calls=[
                {"name": "add_tool", "args": {"a": 1, "b": 2}, "id": "a"},
                {"name": "add_tool", "args": {"a": 3, "b": 4}, "id": "b"},
            ],
        ),
        final(10),
    ]
    result = run_langchain_agent(ScriptedChat(replies=responses), "MOCK task", **{field: value})
    assert (
        result.status == "budget_exceeded" and result.error_type == reason and result.answer is None
    )


@pytest.mark.parametrize(
    "name,args,error",
    [("unknown", {}, "unknown_tool"), ("add_tool", {"a": True, "b": 2}, "invalid_arguments")],
)
def test_framework_bad_calls_return_correlated_errors(name, args, error):
    model = ScriptedChat(replies=[chat_call(name, args, "bad"), final()])
    result = run_langchain_agent(model, "test")
    assert result.status == "completed"
    messages = [m for m in model.seen[-1] if isinstance(m, ToolMessage)]
    assert len(messages) == 1 and messages[0].tool_call_id == "bad"
    assert messages[0].status == "error" and error in messages[0].content


def test_framework_model_timeout_retries_and_real_usage_limit():
    gate = Event()

    def slow(messages):
        gate.wait(3)
        return final()

    started = perf_counter()
    try:
        result = run_langchain_agent(ScriptedChat(replies=[slow]), "task", timeout=0.04)
        assert result.status == "timeout" and perf_counter() - started < 1
    finally:
        gate.set()
    model = ScriptedChat(replies=[ConnectionError("test"), final()])
    assert run_langchain_agent(model, "task", max_retries=1).status == "completed"
    assert model.index == 2
    message = final()
    message.usage_metadata = {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20}
    result = run_langchain_agent(ScriptedChat(replies=[message]), "task", max_total_tokens=10)
    assert result.status == "budget_exceeded" and result.usage["total_tokens"] == 20


@pytest.mark.parametrize("kind", ["direct", "multiple", "multi"])
def test_same_business_plans_native_and_framework(kind):
    from langchain_core.messages import AIMessage

    if kind == "direct":
        native = [ModelReply(text="hello")]
        framework = [final()]
        expected = []
    elif kind == "multiple":
        native = [
            ModelReply(
                calls=(
                    ToolCall("add", {"a": 15, "b": 27}, "a"),
                    ToolCall("add", {"a": 48, "b": 4}, "b"),
                )
            ),
            ModelReply(text="52"),
        ]
        framework = [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "add_tool", "args": {"a": 15, "b": 27}, "id": "a"},
                    {"name": "add_tool", "args": {"a": 48, "b": 4}, "id": "b"},
                ],
            ),
            final(52),
        ]
        expected = ["add", "add"]
    else:
        native = [
            ModelReply(calls=(ToolCall("lookup_product_spec", {"model": "MOCK-SW-48"}, "a"),)),
            ModelReply(calls=(ToolCall("add", {"a": 48, "b": 4}, "b"),)),
            ModelReply(text="52"),
        ]
        framework = [
            chat_call("lookup_product_spec_tool", {"model": "MOCK-SW-48"}, "a"),
            chat_call("add_tool", {"a": 48, "b": 4}, "b"),
            final(52),
        ]
        expected = ["lookup_product_spec", "add"]
    original = run_agent_loop(NativeScript(native), "TEST business task")
    wrapped = run_langchain_agent(ScriptedChat(replies=framework), "TEST business task")
    assert original.status == wrapped.status == "completed"
    assert [e["tool_name"] for e in original.events if e["event"] == "ACTION"] == expected
    assert [
        e["tool_name"].removesuffix("_tool") for e in wrapped.events if e["event"] == "TOOL_RESULT"
    ] == expected


def test_framework_tool_exception_and_invalid_output_are_diagnostic(monkeypatch):
    from agent_demo.tools import TOOL_REGISTRY

    def broken(**kwargs):
        raise RuntimeError("TEST failure")

    monkeypatch.setitem(TOOL_REGISTRY, "add", broken)
    result = run_langchain_agent(
        ScriptedChat(replies=[chat_call("add_tool", {"a": 1, "b": 2}), final()]), "test"
    )
    assert any(e.get("error_type") == "tool_execution_failed" for e in result.events)
    invalid = chat_call(
        "AgentAnswer", {"model": "MOCK-SW-48", "conclusion": "MOCK", "total_ports": "invalid"}
    )
    result = run_langchain_agent(ScriptedChat(replies=[invalid]), "test", max_model_rounds=1)
    assert result.status != "completed" and result.answer is None
