import pytest

from agent_demo.agents.langchain_agent import (
    AgentAnswer,
    add_tool,
    build_agent,
    lookup_product_spec_tool,
)


def test_pydantic_answer_and_wrapped_tools_reuse_dispatcher():
    answer = AgentAnswer(model="MOCK-SW-48", conclusion="52 total ports", total_ports=52)
    assert answer.model == "MOCK-SW-48"
    assert add_tool.invoke({"a": 48, "b": 4}) == 52.0
    assert lookup_product_spec_tool.invoke({"model": "MOCK-SW-48"})["downlink_ports"] == 48


def test_invalid_tool_arguments_are_rejected_by_wrapper():
    # Pydantic rejects at the schema boundary before Dispatcher; ValidationError
    # is a ValueError subclass. Do not depend on a later concrete exception name.
    with pytest.raises(ValueError):
        lookup_product_spec_tool.invoke({"model": "REAL-SW-48"})


def test_create_agent_is_the_selected_api(monkeypatch):
    captured = {}

    class FakeGraph:
        def invoke(self, *args, **kwargs):
            return {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return FakeGraph()

    monkeypatch.setattr("agent_demo.agents.langchain_agent.create_agent", fake_create_agent)
    graph, rounds = build_agent("fake:model", max_model_rounds=4)
    assert rounds == 4
    assert captured["tools"]
    assert captured["response_format"] is AgentAnswer
    assert graph.__class__ is FakeGraph
