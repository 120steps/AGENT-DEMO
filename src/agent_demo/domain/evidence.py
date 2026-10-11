"""MOCK evidence, with explicit unknown provenance fields."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agent_demo.domain.requirements import Value


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    attribute: str = Field(min_length=1)
    actual_value: Value | None = None
    unit: str | None = None
    source_text: str | None = None
    source_document: str | None = None
    source_version: str | None = None
    source_location: str | None = None
    applicable_conditions: dict[str, str] = Field(default_factory=dict)
    source_type: Literal["mock"]
