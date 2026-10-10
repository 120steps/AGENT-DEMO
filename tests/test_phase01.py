"""Offline safety and provider-protocol checks; no API credentials required."""

import json
from types import SimpleNamespace

import pytest
from google.genai import types

from agent_demo.agents.tool_calling import ModelReply, ToolCall, run_tool_calling
from agent_demo.config import ModelSettings, load_model_settings
from agent_demo.integrations.gemini import GeminiClient
from agent_demo.tools import TOOL_REGISTRY, add, dispatch


class FakeClient:
    def __init__(self, first, final=ModelReply(text="42")):
        self.reply = first
        self.final = final
        self.received = None

    def first(self, prompt, definitions):
        return self.reply

    def finish(self, prompt, first, outputs, definitions):
        self.received = (first, outputs)
        return self.final


def test_local_tools_and_mock_not_found():
    assert add(15, 27) == 42
    result = dispatch("lookup_product_spec", {"model": "MOCK-SW-48"})["result"]
    assert (result["downlink_ports"], result["uplink_ports"], result["source_type"]) == (
        48,
        4,
        "mock",
    )
    assert (
        dispatch("lookup_product_spec", {"model": "MOCK-SW-99"})["result"]["status"] == "not_found"
    )


@pytest.mark.parametrize("value", [True, False, "15", None, float("nan"), float("inf"), 10**400])
def test_add_does_not_coerce_unsafe_types(value):
    with pytest.raises(ValueError):
        add(value, 2)
    assert dispatch("add", {"a": value, "b": 2})["error_type"] == "invalid_arguments"


@pytest.mark.parametrize(
    "arguments",
    [
        "not-json",
        "[]",
        "null",
        '{"a":NaN,"b":2}',
        '{"a":1,"a":2,"b":3}',
        {"a": 1},
        {"a": 1, "b": 2, "path": "x"},
        {"a": 1, "b": "2"},
    ],
)
def test_invalid_json_and_parameters_rejected(arguments):
    assert dispatch("add", arguments)["error_type"] == "invalid_arguments"


@pytest.mark.parametrize("model", ["../../secret", "cmd.exe", True, "MOCK-SW-48\n"])
def test_model_cannot_be_path_or_command(model):
    assert dispatch("lookup_product_spec", {"model": model})["error_type"] == "invalid_arguments"


def test_unknown_tool_is_rejected_before_execution():
    assert dispatch("os.system", '{"command":"echo unsafe"}') == {
        "status": "error",
        "error_type": "unknown_tool",
    }


def test_execution_error_and_api_error_do_not_leak_exception_text(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("secret-bearing exception")

    monkeypatch.setitem(TOOL_REGISTRY, "add", fail)
    client = FakeClient(ModelReply(calls=(ToolCall("add", {"a": 1, "b": 2}, "c1"),)))
    result = run_tool_calling(client, "calculate")
    assert result.status == "tool_error"
    assert client.received[1][0]["error_type"] == "tool_execution_failed"
    assert "secret-bearing" not in json.dumps(result.events)
    monkeypatch.setattr(client, "first", fail)
    result = run_tool_calling(client, "calculate")
    assert result.status == "api_error"
    assert result.events[-1]["error_type"] == "RuntimeError"
    assert "secret-bearing" not in json.dumps(result.events)


def test_direct_answer_does_not_dispatch_or_send_second_request():
    client = FakeClient(ModelReply(text="Hello"))
    result = run_tool_calling(client, "Hi")
    assert result.answer == "Hello"
    assert client.received is None
    assert not any(event["event"] == "TOOL_CALL" for event in result.events)


def test_offline_round_preserves_order_and_call_ids():
    calls = (
        ToolCall("add", '{"a":15,"b":27}', "sum-1"),
        ToolCall("lookup_product_spec", {"model": "MOCK-SW-24"}, "spec-2"),
    )
    client = FakeClient(ModelReply(calls=calls))
    result = run_tool_calling(client, "calculate and look up")
    assert result.status == "completed"
    assert client.received[0].calls == calls
    assert client.received[1][0]["result"] == 42
    assert client.received[1][1]["result"]["downlink_ports"] == 24
    results = [event for event in result.events if event["event"] == "TOOL_RESULT"]
    assert [event["tool_call_id"] for event in results] == ["sum-1", "spec-2"]
    assert all(event["run_id"] == result.run_id for event in result.events)


def test_second_round_request_stops_without_execution():
    client = FakeClient(
        ModelReply(calls=(ToolCall("add", {"a": 1, "b": 2}, "c1"),)),
        ModelReply(calls=(ToolCall("add", {"a": 3, "b": 4}, "c2"),)),
    )
    result = run_tool_calling(client, "calculate")
    assert result.status == "additional_tool_call_required"
    assert len([event for event in result.events if event["event"] == "TOOL_EXECUTION"]) == 1


@pytest.mark.parametrize(
    "reply",
    [
        ModelReply(),
        ModelReply(calls=(ToolCall("add", {}, "same"), ToolCall("add", {}, "same"))),
        ModelReply(calls=(ToolCall("", {}, None),)),
    ],
)
def test_incomplete_or_ambiguous_response_rejected(reply):
    assert run_tool_calling(FakeClient(reply), "question").status == "response_error"


@pytest.mark.parametrize(
    "reply",
    [
        ModelReply(text=None),
        ModelReply(calls=(None,)),
        ModelReply(calls=(ToolCall("add", {}, []),)),
    ],
)
def test_malformed_adapter_values_are_response_errors(reply):
    assert run_tool_calling(FakeClient(reply), "question").status == "response_error"


def sdk_response(parts, reason=types.FinishReason.STOP):
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(content=types.Content(role="model", parts=parts), finish_reason=reason)
        ],
        model_version="offline-protocol-fixture",
    )


@pytest.mark.parametrize("call_id", ["provider-id-1", None])
def test_gemini_manual_protocol_preserves_content_and_optional_id(call_id):
    first_response = sdk_response(
        [
            types.Part(
                function_call=types.FunctionCall(name="add", args={"a": 15, "b": 27}, id=call_id),
                thought_signature=b"opaque-signature",
            ),
        ]
    )
    responses = iter([first_response, sdk_response([types.Part.from_text(text="42")])])
    requests = []

    def generate_content(**kwargs):
        requests.append(kwargs)
        return next(responses)

    sdk = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    client = GeminiClient(ModelSettings("test-only-not-a-key"), sdk_client=sdk)
    result = run_tool_calling(client, "15+27?")
    assert result.status == "completed"
    assert len(requests) == 2
    config = requests[0]["config"]
    assert config.automatic_function_calling.disable is True
    assert config.tool_config.function_calling_config.mode == "AUTO"
    assert [item.name for item in config.tools[0].function_declarations] == [
        "add",
        "lookup_product_spec",
    ]
    assert requests[1]["contents"][1] is first_response.candidates[0].content
    assert requests[1]["contents"][1].parts[0].thought_signature == b"opaque-signature"
    returned = requests[1]["contents"][2].parts[0].function_response
    assert requests[1]["contents"][2].role == "user"
    assert (returned.name, returned.id, returned.response) == (
        "add",
        call_id,
        {"status": "ok", "result": 42},
    )


@pytest.mark.parametrize("reason", [types.FinishReason.MAX_TOKENS, types.FinishReason.SAFETY])
def test_gemini_incomplete_responses_are_not_success(reason):
    sdk = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **kwargs: sdk_response(
                [types.Part.from_text(text="partial")], reason
            )
        )
    )
    result = run_tool_calling(GeminiClient(ModelSettings("test-only"), sdk_client=sdk), "question")
    assert result.status == "response_error"


def test_config_explicit_environment_and_secret_safe_repr():
    settings = load_model_settings(
        {"GEMINI_API_KEY": "test-secret", "GEMINI_MODEL": "gemini-flash-latest"}
    )
    assert "test-secret" not in repr(settings)
    assert settings.model == "gemini-flash-latest"
    with pytest.raises(ValueError):
        load_model_settings({})
    assert load_model_settings({"GOOGLE_API_KEY": "test-fallback"}).api_key == "test-fallback"
