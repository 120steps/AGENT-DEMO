"""Validated business input; decomposition is manual, not an NLP claim."""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictBool, model_validator

from agent_demo.tools import finite_number


def validate_requirement_model(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", value):
        raise ValueError("model must be an explicit safe identifier, not a path or URL")
    return value


def validate_value(value):
    if isinstance(value, str):
        if not value.strip():
            raise ValueError("empty value")
        return value
    return finite_number(value)


Value = Annotated[float | str, BeforeValidator(validate_value)]


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    parent_id: str | None = None
    original_text: str = Field(min_length=1)
    source_location: str = Field(min_length=1)
    model: Annotated[str, BeforeValidator(validate_requirement_model)]
    kind: Literal["atomic", "composite"] = "atomic"
    mandatory: StrictBool = True
    attribute: str | None = None
    operator: Literal[">=", ">", "<=", "<", "=="] | None = None
    expected_value: Value | None = None
    unit: str | None = None
    applicable_conditions: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_shape(self):
        fields = (self.attribute, self.operator, self.expected_value, self.unit)
        if self.kind == "atomic" and any(value is None or value == "" for value in fields):
            raise ValueError("atomic requirement needs attribute/operator/value/unit")
        if self.kind == "composite" and any(value is not None for value in fields):
            raise ValueError("composite requirement must be decomposed")
        if isinstance(self.expected_value, str) and self.operator != "==":
            raise ValueError("categorical values only support ==")
        return self
