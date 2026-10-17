"""Google's official SDK with automatic function execution explicitly disabled."""

from google import genai
from google.genai import types

from agent_demo.agents.tool_calling import ModelReply, ResponseFormatError, ToolCall
from agent_demo.config import ModelSettings


class GeminiClient:
    def __init__(self, settings: ModelSettings, sdk_client=None):
        self.model = settings.model
        self.max_output_tokens = 2048
        self.timeout_ms = 30000
        self.sdk = sdk_client or genai.Client(
            api_key=settings.api_key,
            http_options=types.HttpOptions(
                timeout=30000, retry_options=types.HttpRetryOptions(attempts=1)
            ),
        )

    def close(self):
        self.sdk.close()

    def for_run(self, *, max_output_tokens, timeout):
        from copy import copy

        client = copy(self)
        client.max_output_tokens = max_output_tokens
        client.timeout_ms = max(1, int(timeout * 1000))
        return client

    def _config(self, definitions):
        declarations = [
            types.FunctionDeclaration(
                name=definition["name"],
                description=definition["description"],
                parameters_json_schema=definition["parameters"],
            )
            for definition in definitions
        ]
        return types.GenerateContentConfig(
            http_options=types.HttpOptions(timeout=self.timeout_ms),
            tools=[types.Tool(function_declarations=declarations)],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="AUTO")
            ),
            system_instruction=(
                "Use the declared tools for arithmetic and MOCK switch specifications. "
                "MOCK data is simulated, not real product evidence. For greetings answer directly. "
                "After receiving results, explain them faithfully; never fabricate tool results."
            ),
            temperature=0,
            max_output_tokens=self.max_output_tokens,
        )

    @staticmethod
    def _parse(response):
        candidates = response.candidates or []
        if len(candidates) != 1:
            raise ResponseFormatError("Expected one candidate")
        candidate = candidates[0]
        if candidate.finish_reason != types.FinishReason.STOP:
            raise ResponseFormatError("Incomplete or blocked response")
        content = candidate.content
        if content is None or content.role != "model" or not content.parts:
            raise ResponseFormatError("Missing model content")
        calls = []
        text = []
        for part in content.parts:
            if part.function_call is not None:
                call = part.function_call
                if call.partial_args or call.will_continue:
                    raise ResponseFormatError("Streaming/partial calls are out of scope")
                calls.append(ToolCall(call.name, call.args, call.id))
            elif part.text and not part.thought:
                text.append(part.text)
            elif not part.thought and not part.thought_signature:
                raise ResponseFormatError("Unsupported response part")
        # Preserve the original content object, including opaque thought signatures.
        metadata = getattr(response, "usage_metadata", None)
        usage = {}
        if metadata:
            usage = {
                "input_tokens": metadata.prompt_token_count or 0,
                "output_tokens": metadata.candidates_token_count or 0,
                "total_tokens": metadata.total_token_count or 0,
            }
        return ModelReply("".join(text), tuple(calls), content, response.model_version, usage)

    @staticmethod
    def _user(prompt):
        return types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    def first(self, prompt, definitions):
        return self._parse(
            self.sdk.models.generate_content(
                model=self.model, contents=[self._user(prompt)], config=self._config(definitions)
            )
        )

    def finish(self, prompt, first, outputs, definitions):
        return self.continue_turn(prompt, [first], outputs, definitions)

    def continue_turn(self, prompt, history, outputs, definitions):
        last = history[-1][0] if isinstance(history[-1], tuple) else history[-1]
        if len(last.calls) != len(outputs):
            raise ResponseFormatError("Tool output count mismatch")
        responses = []
        for call, output in zip(last.calls, outputs, strict=True):
            response = types.FunctionResponse(name=call.name, response=output)
            if call.call_id is not None:
                response.id = call.call_id
            responses.append(types.Part(function_response=response))
        contents = [self._user(prompt)]
        for item in history:
            prior, prior_outputs = item if isinstance(item, tuple) else (item, None)
            contents.append(prior.context)
            if prior_outputs is not None:
                prior_parts = []
                for prior_call, prior_output in zip(prior.calls, prior_outputs, strict=True):
                    prior_response = types.FunctionResponse(
                        name=prior_call.name, response=prior_output
                    )
                    if prior_call.call_id is not None:
                        prior_response.id = prior_call.call_id
                    prior_parts.append(types.Part(function_response=prior_response))
                contents.append(types.Content(role="user", parts=prior_parts))
        # Loop history already contains each completed call/result pair. The
        # Phase 1 finish path supplies an unpaired last reply instead.
        if not isinstance(history[-1], tuple):
            contents.append(types.Content(role="user", parts=responses))
        return self._parse(
            self.sdk.models.generate_content(
                model=self.model,
                contents=contents,
                config=self._config(definitions),
            )
        )
