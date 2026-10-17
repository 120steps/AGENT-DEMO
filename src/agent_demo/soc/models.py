"""Application inputs reuse the existing requirement/evidence business contract."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from agent_demo.domain.evidence import Evidence
from agent_demo.domain.requirements import Requirement


class SOCInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    source_type: Literal["mock", "real_rag"]
    requirements: list[Requirement] = Field(min_length=1, max_length=100)
    configuration: dict[str, str] = Field(default_factory=dict)
    evidences: list[Evidence] | None = None
    input_confirmed: StrictBool = False

    @model_validator(mode="after")
    def single_model(self):
        if len({r.model for r in self.requirements}) != 1:
            raise ValueError("first release requires one explicit model")
        if len([r for r in self.requirements if r.kind == "atomic"]) > 20:
            raise ValueError("at most 20 atomic requirements")
        if self.source_type == "real_rag" and self.evidences is not None:
            raise ValueError("real evidence must come from configured HTTP retrieval")
        if self.source_type == "mock" and any(
            not r.model.startswith("MOCK-") for r in self.requirements
        ):
            raise ValueError("MOCK tasks must use MOCK model identifiers")
        if self.evidences is not None and any(e.source_type != "mock" for e in self.evidences):
            raise ValueError("only explicitly MOCK fixture evidence is accepted")
        return self
