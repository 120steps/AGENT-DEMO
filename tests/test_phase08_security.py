"""Adversarial regression of actual boundaries and evaluator safety negative controls."""

import json
from pathlib import Path

import pytest

from agent_demo.evaluation.metrics import aggregate
from agent_demo.evaluation.models import CaseResult, Observation
from agent_demo.evaluation.runner import execute_cases, load_cases
from agent_demo.evaluation.security import violations
from agent_demo.observability import Trace
from agent_demo.persistence.operations import OperationError, OperationLedger

DATASET = Path(__file__).resolve().parents[1] / "eval/agent_test_cases.json"


@pytest.mark.parametrize(
    "case_id",
    [
        "tool-unknown",
        "tool-invalid",
        "tool-budget",
        "review-pending",
        "review-reject",
        "review-modify",
        "review-stale",
        "review-repeat-resume",
        "review-repeat-approve",
        "review-idempotent-crash",
        "review-path-traversal",
        "review-overwrite",
        "rag-injection",
        "rag-forged",
        "rag-page-mismatch",
        "mcp-unauthorized",
        "mcp-invalid",
        "mcp-untrusted",
    ],
)
def test_actual_security_boundary(case_id, tmp_path):
    case = next(c for c in load_cases(DATASET) if c.case_id == case_id)
    result = execute_cases([case], tmp_path)[0]
    assert result.outcome == "PASS", (result.error_type, result.mismatches)
    assert not any(violations(result.actual).values())
    if case_id == "rag-injection":
        assert result.actual.facts["business_status"] == "PENDING"
        assert result.actual.facts["awaiting_review"] and result.actual.facts["files"] == 0
        assert not any(t["name"] == "unknown_tool" and t["executed"] for t in result.actual.tools)


@pytest.mark.parametrize(
    "observation,key",
    [
        (Observation("completed", unauthorized_writes=1), "unauthorized_writes"),
        (
            Observation("FC", decisions=[{"proposed_status": "FC", "evidence_ids": ["invented"]}]),
            "unsupported_fc",
        ),
        (
            Observation("completed", citations=[{"accepted": True, "membership_valid": False}]),
            "accepted_forged_citations",
        ),
        (
            Observation(
                "completed",
                citations=[
                    {"accepted": True, "membership_valid": True, "source_consistent": False}
                ],
            ),
            "accepted_forged_citations",
        ),
    ],
)
def test_hard_gate_fails_even_with_pass_label(observation, key):
    case = load_cases(DATASET)[0]
    row = CaseResult(
        case.case_id, case.category, case.execution_mode, "run", "PASS", observation, 1
    )
    result = aggregate([row], [case])
    assert result["safety"][key] == 1
    assert not result["hard_gate_passed"]


def test_trace_drops_credentials_payloads_and_untrusted_names(tmp_path):
    secret = "sk-TEST-PRIVATE-TOKEN"
    path = tmp_path / "trace.jsonl"
    trace = Trace(path)
    trace.emit(
        "TOOL_RESULT",
        tool_name=secret,
        tool_call_id=secret,
        error_type=secret,
        prompt=secret,
        arguments={"api_key": secret},
        document=secret,
        headers={"Authorization": "Bearer " + secret},
        answer=secret,
    )
    raw = path.read_text("utf-8")
    assert secret not in raw and "Bearer" not in raw
    item = json.loads(raw)
    assert item["tool_name"] == "unknown_tool" and item["error_type"] == "redacted"
    assert item["tool_call_id"].startswith("ref-")
    assert not {"prompt", "arguments", "document", "headers", "answer"} & item.keys()


def test_actual_outside_file_is_unchanged(tmp_path):
    victim = tmp_path / "existing-private.json"
    victim.write_bytes(b"TEST existing bytes")
    with OperationLedger(tmp_path / "ledger.sqlite", tmp_path / "outputs/phase05") as ledger:
        with pytest.raises(OperationError):
            ledger.execute("a" * 64, {"document_status": "DRAFT"}, victim)
    assert victim.read_bytes() == b"TEST existing bytes"
    assert list((tmp_path / "outputs/phase05").glob("*.json")) == []
