"""Real SQLite recovery of reconstructed Phase 5 MOCK checkpoint JSON.

These tests model the old optional-field layout, not an arbitrary migration tool
or a claim that every historic checkpoint format is supported.
"""

import json
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver

from agent_demo.domain.mock_cases import complete_evidence, requirements
from agent_demo.graphs.review_graph import (
    build_review_graph,
    digest,
    resume_review,
    snapshot_digest,
    start_review,
    thread_config,
)
from agent_demo.persistence.operations import OperationLedger

PHASE6_EVIDENCE_FIELDS = {
    "source",
    "document_id",
    "document_hash",
    "chunk_id",
    "page",
    "page_number_semantics",
    "retrieval_time",
    "retrieval_query",
    "metadata",
    "origin_verified",
    "extraction_method",
}


@contextmanager
def opened_graph(project):
    runtime = project / "runtime"
    runtime.mkdir(exist_ok=True)
    with OperationLedger(runtime / "operations.sqlite", project / "outputs" / "phase05") as ledger:
        with SqliteSaver.from_conn_string(str(runtime / "checkpoints.sqlite")) as saver:
            saver.setup()
            yield build_review_graph(saver, ledger), ledger


def old_evidence(items):
    return [
        {key: deepcopy(value) for key, value in item.items() if key not in PHASE6_EVIDENCE_FIELDS}
        for item in items
    ]


def response(snapshot, action="approve", **updates):
    return {
        "action": action,
        "review_id": snapshot["review_id"],
        "review_version": snapshot["review_version"],
        "snapshot_digest": snapshot["snapshot_digest"],
        **updates,
    }


def store_old_pending_checkpoint(graph, ledger, thread):
    state = start_review(
        graph, thread, requirements(), evidences=complete_evidence(), run_id="legacy-phase05-run"
    )
    business = deepcopy(state["business_result"])
    # Do not weaken or change business decisions to make a changed algorithm
    # appear compatible: these strings are exactly the Phase 5 MOCK contract.
    leaf_decisions = [
        item for item in business["decisions"] if item["validation_result"] == "ready"
    ]
    assert leaf_decisions
    requirements_by_id = {item["id"]: item for item in business["requirements"]}
    evidence_by_id = {item["id"]: item for item in business["evidences"]}
    for item in leaf_decisions:
        requirement = requirements_by_id[item["requirement_id"]]
        evidence = evidence_by_id[item["evidence_ids"][0]]
        expected_reason = (
            "Applicable MOCK evidence satisfies rule"
            f": {requirement['attribute']} actual={evidence['actual_value']} {evidence['unit']}; "
            f"required {requirement['operator']} {requirement['expected_value']} "
            f"{requirement['unit']}"
        )
        assert item["reason"] == expected_reason
    assert business["decisions"][-1]["reason"].startswith("MOCK conservative composite policy: ")
    decisions_before = deepcopy(business["decisions"])
    business["evidences"] = old_evidence(business["evidences"])
    snapshot = deepcopy(state["review_snapshot"])
    snapshot["business_result"] = deepcopy(business)
    # Reconstruct the historical binding over the historical JSON, rather than
    # retaining an ID generated from Phase 6's newly inserted default fields.
    operation_id = digest(
        {
            "run": state["run_id"],
            "thread": thread,
            "version": 1,
            "result": business,
            "configuration": state["configuration"],
            "root": str(ledger.output_root),
        }
    )
    snapshot["proposed_action"]["operation_id"] = operation_id
    snapshot["proposed_action"]["target_path"] = str(ledger.output_root / f"{operation_id}.json")
    snapshot["review_id"] = digest({"operation": operation_id, "purpose": "human_review"})
    snapshot["snapshot_digest"] = snapshot_digest(snapshot)
    graph.update_state(
        thread_config(thread),
        {
            "business_result": business,
            "evidence_input": old_evidence(state["evidence_input"]),
            "review_snapshot": snapshot,
            "review_history": {"1": {"snapshot": deepcopy(snapshot)}},
        },
        as_node="prepare_review",
    )
    # Establish the real human_review interrupt for the updated persisted state.
    graph.invoke(None, thread_config(thread))
    saved = graph.get_state(thread_config(thread))
    assert saved.next == ("human_review",)
    assert saved.values["review_snapshot"] == snapshot
    assert saved.values["business_result"]["decisions"] == decisions_before
    assert saved.values["status"] == "awaiting_review"
    assert ledger.get(operation_id) is None
    return deepcopy(snapshot)


def assert_old_snapshot_preserved(snapshot, expected):
    assert snapshot == expected
    assert snapshot["snapshot_digest"] == snapshot_digest(snapshot)
    assert all(
        not (PHASE6_EVIDENCE_FIELDS & set(item))
        for item in snapshot["business_result"]["evidences"]
    )


def test_pending_phase05_sqlite_checkpoint_approves_after_optional_evidence_fields_added(tmp_path):
    thread = "legacy-pending"
    with opened_graph(tmp_path) as (graph, ledger):
        historical = store_old_pending_checkpoint(graph, ledger, thread)
    with opened_graph(tmp_path) as (graph, ledger):
        restored = graph.get_state(thread_config(thread)).values
        assert_old_snapshot_preserved(restored["review_snapshot"], historical)
        completed = resume_review(graph, thread, response(historical))
        assert completed["status"] == "completed", completed.get("error_type")
        artifact = Path(completed["operation_result"]["path"])
        bytes_before, mtime_before = artifact.read_bytes(), artifact.stat().st_mtime_ns
        published = json.loads(bytes_before)
        assert_old_snapshot_preserved(published["review_snapshot"], historical)
        assert published["source_type"] == "mock"
        assert published["human_review_status"] == "approved"
        assert ledger.get(historical["proposed_action"]["operation_id"])["status"] == "completed"
    # A fresh graph/connection also verifies an already completed old-schema
    # approval without adding defaults to the immutable approved artifact.
    with opened_graph(tmp_path) as (graph, ledger):
        repeated = resume_review(graph, thread, response(historical))
        assert repeated["status"] == "completed"
        assert_old_snapshot_preserved(repeated["review_snapshot"], historical)
        assert (artifact.read_bytes(), artifact.stat().st_mtime_ns) == (bytes_before, mtime_before)
        assert list(ledger.output_root.glob("*.json")) == [artifact]


def test_legacy_checkpoint_modify_revalidates_new_version_and_rejects_old_approval(tmp_path):
    thread = "legacy-modify"
    with opened_graph(tmp_path) as (graph, ledger):
        historical = store_old_pending_checkpoint(graph, ledger, thread)
    changed = old_evidence(complete_evidence())
    next(item for item in changed if item["attribute"] == "downlink_ports")["actual_value"] = 24
    with opened_graph(tmp_path) as (graph, ledger):
        modified = resume_review(
            graph, thread, response(historical, "modify", modification={"evidences": changed})
        )
        assert modified["status"] == "awaiting_review"
        assert modified["review_version"] == 2
        assert modified["business_result"]["overall_status"] == "NC"
        assert_old_snapshot_preserved(modified["review_history"]["1"]["snapshot"], historical)
        with pytest.raises(ValueError, match="stale"):
            resume_review(graph, thread, response(historical))
        assert not list(ledger.output_root.glob("*.json"))
        new_snapshot = deepcopy(modified["review_snapshot"])
    with opened_graph(tmp_path) as (graph, ledger):
        completed = resume_review(graph, thread, response(new_snapshot))
        assert completed["status"] == "completed", completed.get("error_type")
        assert completed["business_result"]["overall_status"] == "NC"
        artifact = Path(completed["operation_result"]["path"])
        published = json.loads(artifact.read_bytes())
        assert published["review_snapshot"]["review_version"] == 2
        assert published["review_snapshot"]["business_result"]["overall_status"] == "NC"
        assert ledger.get(historical["proposed_action"]["operation_id"]) is None
        before = artifact.read_bytes(), artifact.stat().st_mtime_ns
        repeated = resume_review(graph, thread, response(new_snapshot))
        assert repeated["status"] == "completed"
        assert (artifact.read_bytes(), artifact.stat().st_mtime_ns) == before
        assert list(ledger.output_root.glob("*.json")) == [artifact]
