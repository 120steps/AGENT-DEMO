"""Evaluation contracts, separate from the existing business domain models."""

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,79}$")
    category: Literal["tool", "compliance", "review", "rag", "mcp"]
    description: str = Field(min_length=1)
    input: dict[str, Any]
    expected_status: str
    expected_facts: dict[str, Any] = Field(default_factory=dict)
    required_actions: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    expected_evidence: dict[str, Any] = Field(default_factory=dict)
    data_source: str
    execution_mode: Literal["offline_mock", "mcp_stdio", "mcp_memory", "real_llm", "real_rag"]


@dataclass
class Observation:
    status: str
    facts: dict = field(default_factory=dict)
    actions: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    tools: list[dict] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)
    model_calls: int = 0
    retrieval_calls: int = 0
    token_usage: dict | None = None
    model_latency_ms: float | None = None
    tool_latency_ms: float | None = None
    unauthorized_writes: int = 0


@dataclass
class CaseResult:
    case_id: str
    category: str
    execution_mode: str
    run_id: str
    outcome: str
    actual: Observation | None
    elapsed_ms: float
    mismatches: list[str] = field(default_factory=list)
    error_type: str | None = None
