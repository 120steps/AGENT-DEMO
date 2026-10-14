"""MOCK or real RAG evidence, with explicit unknown and verified provenance fields."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

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
    source_type: Literal["mock", "real_rag"]
    source: str | None = None
    document_id: str | None = None
    document_hash: str | None = None
    chunk_id: str | StrictInt | None = None
    page: StrictInt | None = None
    page_number_semantics: Literal["unknown", "pdf_physical_1_based"] = "unknown"
    retrieval_time: str | None = None
    retrieval_query: str | None = None
    metadata: dict | None = None
    origin_verified: StrictBool = False
    extraction_method: Literal["unknown", "deterministic_spec_line"] = "unknown"
