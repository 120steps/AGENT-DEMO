"""Real SQLite and filesystem tests for Phase 5 approved-action publication."""

import hashlib
import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import TypedDict

import pytest
from langgraph.graph import END, START, StateGraph

from agent_demo.persistence.operations import OperationError, OperationLedger, canonical_payload


@pytest.fixture
def operation_paths(tmp_path):
    return tmp_path / "runtime" / "operations.sqlite", tmp_path / "outputs" / "phase05"


@pytest.fixture
def draft():
    return {"source_type": "mock", "artifact_status": "DRAFT", "decision": "FC"}


def test_completed_operation_survives_connection_restart(operation_paths, draft):
    db, output = operation_paths
    with OperationLedger(db, output) as ledger:
        first = ledger.execute("review-1", draft, output / "review-1.json")
        assert ledger.get("review-1")["status"] == "completed"
        assert not first["reused"]
    with OperationLedger(db, output) as ledger:
        second = ledger.execute("review-1", dict(reversed(list(draft.items()))), "review-1.json")
        assert second["reused"]
        assert first["sha256"] == second["sha256"]
        assert ledger.get("review-1")["completed_at"]
    assert json.loads((output / "review-1.json").read_text(encoding="utf-8")) == draft
    assert len(list(output.glob("*.json"))) == 1
    assert not list(output.glob("*.tmp"))


def test_connection_is_closed_after_context(operation_paths):
    with OperationLedger(*operation_paths) as ledger:
        assert ledger.get("missing") is None
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        ledger.get("missing")


def test_operation_cannot_be_rebound_to_modified_payload(operation_paths, draft):
    db, output = operation_paths
    with OperationLedger(db, output) as ledger:
        ledger.execute("approved", draft, "approved.json")
        with pytest.raises(OperationError, match="different content"):
            ledger.execute("approved", dict(draft, decision="NC"), "approved.json")
    assert json.loads((output / "approved.json").read_text()) == draft


@pytest.mark.parametrize("change", ["remove", "tamper"])
def test_completed_artifact_is_verified_and_never_blindly_recreated(operation_paths, draft, change):
    db, output = operation_paths
    target = output / "completed.json"
    with OperationLedger(db, output) as ledger:
        ledger.execute("completed", draft, target)
        if change == "remove":
            target.unlink()
        else:
            target.write_text("tampered", encoding="utf-8")
        with pytest.raises(OperationError):
            ledger.execute("completed", draft, target)
        assert ledger.get("completed")["status"] == "completed"
    assert target.exists() == (change == "tamper")
    if target.exists():
        assert target.read_text() == "tampered"


def test_preexisting_file_without_trusted_record_is_never_adopted(operation_paths, draft):
    db, output = operation_paths
    with OperationLedger(db, output) as ledger:
        target = output / "unknown.json"
        target.write_bytes(canonical_payload(draft))
        with pytest.raises(OperationError, match="no trusted operation record"):
            ledger.execute("unknown", draft, target)
        assert ledger.get("unknown") is None


def test_failure_after_publish_leaves_prepared_intent_and_recovers(operation_paths, draft):
    db, output = operation_paths

    def simulated_crash():
        raise RuntimeError("simulated failure before checkpoint/ledger completion")

    with OperationLedger(db, output) as ledger:
        with pytest.raises(RuntimeError):
            ledger.execute("recover", draft, "recover.json", after_publish=simulated_crash)
        assert ledger.get("recover")["status"] == "prepared"
        original = (output / "recover.json").read_bytes()
    with OperationLedger(db, output) as ledger:
        result = ledger.execute("recover", draft, "recover.json")
        assert result["reused"]
        assert ledger.get("recover")["status"] == "completed"
    assert (output / "recover.json").read_bytes() == original
    assert len(list(output.glob("*.json"))) == 1


def test_real_process_exit_after_publish_is_recovered_by_new_process(operation_paths, draft):
    db, output = operation_paths
    source = """
import json, os, sys
from pathlib import Path
from agent_demo.persistence.operations import OperationLedger
db, output, mode = sys.argv[1:4]
with OperationLedger(Path(db), Path(output)) as ledger:
    result = ledger.execute('process-crash', json.loads(sys.argv[4]), 'process-crash.json',
                            after_publish=(lambda: os._exit(73)) if mode == 'crash' else None)
    print(json.dumps(result))
"""
    command = [sys.executable, "-c", source, str(db), str(output)]
    crashed = subprocess.run(
        command + ["crash", json.dumps(draft)], capture_output=True, timeout=30
    )
    assert crashed.returncode == 73
    with OperationLedger(db, output) as ledger:
        assert ledger.get("process-crash")["status"] == "prepared"
    bytes_before = (output / "process-crash.json").read_bytes()
    recovered = subprocess.run(
        command + ["recover", json.dumps(draft)], capture_output=True, text=True, timeout=30
    )
    assert recovered.returncode == 0, recovered.stderr
    assert json.loads(recovered.stdout)["reused"]
    with OperationLedger(db, output) as ledger:
        assert ledger.get("process-crash")["status"] == "completed"
    assert (output / "process-crash.json").read_bytes() == bytes_before
    assert len(list(output.glob("*.json"))) == 1


def test_corrupt_file_with_prepared_record_is_not_replaced(operation_paths, draft):
    db, output = operation_paths
    with OperationLedger(db, output) as ledger:
        with pytest.raises(RuntimeError):
            ledger.execute(
                "pending",
                draft,
                "pending.json",
                after_publish=lambda: (_ for _ in ()).throw(RuntimeError("crash")),
            )
        (output / "pending.json").write_text("conflicting bytes", encoding="utf-8")
        with pytest.raises(OperationError, match="conflicts"):
            ledger.execute("pending", draft, "pending.json")
        assert ledger.get("pending")["status"] == "prepared"
    assert (output / "pending.json").read_text() == "conflicting bytes"


@pytest.mark.parametrize(
    "bad_path", ["../escape.json", "wrong-name.json", "nested/safe.json", "../phase05/safe.json"]
)
def test_relative_path_traversal_or_uncontrolled_name_is_rejected(operation_paths, draft, bad_path):
    db, output = operation_paths
    with OperationLedger(db, output) as ledger:
        with pytest.raises(OperationError):
            ledger.execute("safe", draft, bad_path)
        assert ledger.get("safe") is None
    assert not list(output.glob("*.json"))


def test_absolute_path_outside_authorized_root_is_rejected(operation_paths, draft, tmp_path):
    db, output = operation_paths
    target = tmp_path / "safe.json"
    with OperationLedger(db, output) as ledger:
        with pytest.raises(OperationError):
            ledger.execute("safe", draft, target)
    assert not target.exists()


@pytest.mark.parametrize("operation_id", ["", "../safe", "safe/child", "x.json", "a" * 129])
def test_invalid_operation_id_is_rejected(operation_paths, draft, operation_id):
    with OperationLedger(*operation_paths) as ledger:
        with pytest.raises(OperationError, match="operation_id"):
            ledger.execute(operation_id, draft, "safe.json")


def test_output_root_must_be_project_phase05_directory(tmp_path):
    with pytest.raises(OperationError, match="outputs/phase05"):
        OperationLedger(tmp_path / "db.sqlite", tmp_path / "elsewhere")
    assert not (tmp_path / "elsewhere").exists()


def test_output_symlink_is_rejected(operation_paths, draft, tmp_path):
    db, output = operation_paths
    outside = tmp_path / "outside"
    outside.mkdir()
    output.parent.mkdir()
    try:
        output.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        if sys.platform != "win32":
            pytest.skip(f"symlink creation unavailable: {exc.__class__.__name__}")
        # Windows commonly denies symbolic links but permits a local NTFS junction.
        junction = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(output), str(outside)],
            capture_output=True,
            timeout=10,
        )
        if junction.returncode:
            pytest.skip("neither symlink nor junction creation is available")
    with pytest.raises(OperationError, match="symlinks"):
        OperationLedger(db, output)
    assert not list(outside.iterdir())


@pytest.mark.parametrize("payload", [{"n": float("nan")}, {"n": float("inf")}, {"n": object()}])
def test_invalid_json_never_creates_operation(operation_paths, payload):
    with OperationLedger(*operation_paths) as ledger:
        with pytest.raises(OperationError, match="JSON"):
            ledger.execute("invalid-json", payload, "invalid-json.json")
        assert ledger.get("invalid-json") is None


def test_concurrent_calls_serialize_to_one_local_artifact(operation_paths, draft):
    db, output = operation_paths
    with OperationLedger(db, output):
        pass

    def perform(_):
        with OperationLedger(db, output) as ledger:
            return ledger.execute("concurrent", draft, "concurrent.json")

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(perform, range(8)))
    assert sum(not result["reused"] for result in results) == 1
    assert len(list(output.glob("*.json"))) == 1
    assert all(
        result["sha256"] == hashlib.sha256(canonical_payload(draft)).hexdigest()
        for result in results
    )


def test_operation_target_binding_cannot_move_to_another_root(operation_paths, draft, tmp_path):
    db, output = operation_paths
    with OperationLedger(db, output) as ledger:
        ledger.execute("fixed", draft, "fixed.json")
    another_output = tmp_path / "another-project" / "outputs" / "phase05"
    with OperationLedger(db, another_output) as ledger:
        with pytest.raises(OperationError, match="different content or target"):
            ledger.execute("fixed", draft, "fixed.json")
    assert not list(another_output.glob("*.json"))


def test_ledger_created_on_main_thread_is_usable_by_real_graph_worker(operation_paths, draft):
    class State(TypedDict, total=False):
        result: dict

    with OperationLedger(*operation_paths) as ledger:

        def publish(state):
            return {"result": ledger.execute("graph-worker", draft, "graph-worker.json")}

        builder = StateGraph(State)
        builder.add_node("publish", publish)
        builder.add_edge(START, "publish")
        builder.add_edge("publish", END)
        graph = builder.compile()
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(graph.invoke, {}).result(timeout=15)
        assert result["result"]["status"] == "completed"
        assert ledger.get("graph-worker")["status"] == "completed"


def test_shared_connection_is_serialized_across_worker_threads(operation_paths, draft):
    with OperationLedger(*operation_paths) as ledger:

        def publish(_):
            return ledger.execute("shared", draft, "shared.json")

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(publish, range(8)))
        assert sum(not result["reused"] for result in results) == 1
        assert ledger.get("shared")["status"] == "completed"
    assert len(list(operation_paths[1].glob("*.json"))) == 1
