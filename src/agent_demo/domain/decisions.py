"""Business conclusions are distinct from workflow execution status."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agent_demo.domain.evidence import Evidence
from agent_demo.domain.requirements import Requirement

Status = Literal["FC", "PC", "NC", "PENDING", "ERROR"]


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requirement_id: str
    proposed_status: Status
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    validation_result: str
    missing_items: list[str] = Field(default_factory=list)
    conflict_items: list[str] = Field(default_factory=list)
    review_status: Literal["not_reviewed"] = "not_reviewed"


class WorkflowResult(BaseModel):
    overall_status: Status
    workflow_status: Literal["completed", "failed"]
    decisions: list[Decision]
    errors: dict[str, str]
    requirements: list[Requirement]
    evidences: list[Evidence]
    validation_results: dict[str, dict]
    source_type: Literal["mock"] = "mock"
