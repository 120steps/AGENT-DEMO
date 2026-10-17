"""Explicit scripted models and synthetic TEST PDF, never real LLM/product evidence."""

import hashlib
from io import BytesIO
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from agent_demo.agents.tool_calling import ModelReply


class NativeScript:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.outputs = []
        self.proposals = []

    def _next(self):
        reply = next(self.replies)
        if isinstance(reply, Exception):
            raise reply
        self.proposals.extend(reply.calls)
        return reply

    def first(self, prompt, definitions):
        return self._next()

    def finish(self, prompt, first, outputs, definitions):
        self.outputs.extend(outputs)
        return self._next()

    def continue_turn(self, prompt, history, outputs, definitions):
        self.outputs.extend(outputs)
        return self._next()


class ScriptedChat(BaseChatModel):
    replies: list[Any]
    index: int = 0
    seen: list = Field(default_factory=list)

    @property
    def _llm_type(self):
        return "phase08-scripted-offline-not-llm"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        reply = self.replies[self.index]
        self.index += 1
        if callable(reply):
            reply = reply(messages)
        if isinstance(reply, Exception):
            raise reply
        return ChatResult(generations=[ChatGeneration(message=reply)])


def chat_call(name, arguments, call_id="script-call"):
    return AIMessage(content="", tool_calls=[{"id": call_id, "name": name, "args": arguments}])


def native_final():
    return ModelReply(text="OFFLINE transcript complete; inspect executed tool data.")


def test_pdf(path, text="Downlink ports: 48 count"):
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    content = DecodedStreamObject()
    content.set_data(f"BT /F1 12 Tf 40 740 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(content)
    buffer = BytesIO()
    writer.write(buffer)
    path.write_bytes(buffer.getvalue())
    return hashlib.sha256(buffer.getvalue()).hexdigest()
