"""Human review data, separate from the MOCK business conclusion."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from agent_demo.domain.decisions import WorkflowResult
from agent_demo.domain.evidence import Evidence
from agent_demo.domain.requirements import Requirement


class Modification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirements: list[Requirement] | None = None
    evidences: list[Evidence] | None = None
    configuration: dict[str, str] | None = None

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set:
            raise ValueError("modify requires replacement data")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("use explicit lists/dicts, not null")
        return self


class ReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["approve", "reject", "modify"]
    review_id: str = Field(min_length=1)
    review_version: StrictInt = Field(ge=1)
    snapshot_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    comment: str = ""
    modification: Modification | None = None

    @model_validator(mode="after")
    def check_action(self):
        if (self.action == "modify") != (self.modification is not None):
            raise ValueError("only modify requires modification")
        return self


class ProposedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["write_mock_soc_draft", "write_soc_draft"] = "write_mock_soc_draft"
    operation_id: str
    target_path: str
    document_status: Literal["DRAFT"] = "DRAFT"
    source_type: Literal["mock", "real_rag"] = "mock"


class SOCExportPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["write_soc_excel_draft"] = "write_soc_excel_draft"
    output_root: str
    format_version: Literal["soc-v2"] = "soc-v2"
    document_status: Literal["DRAFT"] = "DRAFT"


class ReviewSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    thread_id: str
    review_id: str
    review_version: StrictInt = Field(ge=1)
    snapshot_digest: str
    business_result: WorkflowResult
    configuration: dict[str, str]
    proposed_action: ProposedAction
    export_policy: SOCExportPolicy | None = None
