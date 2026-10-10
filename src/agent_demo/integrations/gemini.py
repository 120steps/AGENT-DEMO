"""Google's official SDK with automatic function execution explicitly disabled."""

from google import genai
from google.genai import types

from agent_demo.agents.tool_calling import ModelReply, ResponseFormatError, ToolCall
from agent_demo.config import ModelSettings


class GeminiClient:
    def __init__(self, settings: ModelSettings, sdk_client=None):
        self.model = settings.model
        self.sdk = sdk_client or genai.Client(
            api_key=settings.api_key,
            http_options=types.HttpOptions(
                timeout=30000, retry_options=types.HttpRetryOptions(attempts=1)
            ),
        )

    def close(self):
        self.sdk.close()

    @staticmethod
    def _config(definitions):
        declarations = [
            types.FunctionDeclaration(
                name=definition["name"],
                description=definition["description"],
                parameters_json_schema=definition["parameters"],
            )
            for definition in definitions
        ]
        return types.GenerateContentConfig(
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
            max_output_tokens=2048,
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
        return ModelReply("".join(text), tuple(calls), content, response.model_version)

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
        if len(first.calls) != len(outputs):
            raise ResponseFormatError("Tool output count mismatch")
        responses = []
        for call, output in zip(first.calls, outputs, strict=True):
            response = types.FunctionResponse(name=call.name, response=output)
            if call.call_id is not None:
                response.id = call.call_id
            responses.append(types.Part(function_response=response))
        return self._parse(
            self.sdk.models.generate_content(
                model=self.model,
                contents=[
                    self._user(prompt),
                    first.context,
                    # Gemini API Content roles are user/model; a function response
                    # is supplied by the application on the user side of the turn.
                    types.Content(role="user", parts=responses),
                ],
                config=self._config(definitions),
            )
        )
