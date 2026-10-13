"""Real graph, SQLite, subprocess and local-file tests; all business inputs are MOCK."""

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from agent_demo.domain.mock_cases import complete_evidence, requirements
from agent_demo.graphs.compliance_graph import run_workflow
from agent_demo.graphs.review_graph import build_review_graph, resume_review, start_review
from agent_demo.graphs.store_demo import namespace_access, run_store_demo
from agent_demo.persistence.operations import OperationLedger


def config(thread="thread-a"):
    return {"configurable": {"thread_id": thread}, "recursion_limit": 100}


def response(state, action="approve", **updates):
    snapshot = state["review_snapshot"]
    return {
        "action": action,
        "review_id": snapshot["review_id"],
        "review_version": snapshot["review_version"],
        "snapshot_digest": snapshot["snapshot_digest"],
        **updates,
    }


def begin(graph, thread="thread-a"):
    return start_review(graph, thread, requirements(), evidences=complete_evidence())


@pytest.fixture
def ledger(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    with OperationLedger(runtime / "operations.sqlite", tmp_path / "outputs" / "phase05") as item:
        yield item


@pytest.fixture
def graph(ledger):
    return build_review_graph(InMemorySaver(), ledger)


def products(tmp_path):
    return sorted((tmp_path / "outputs" / "phase05").glob("*.json"))


def test_interrupt_contains_actual_business_snapshot_and_no_write(graph, ledger, tmp_path):
    state = begin(graph)
    snapshot = state["review_snapshot"]
    assert state["status"] == "awaiting_review"
    assert state["business_result"]["overall_status"] == "FC"
    assert snapshot["business_result"] == state["business_result"]
    assert snapshot["thread_id"] == "thread-a"
    assert snapshot["run_id"] == state["run_id"]
    assert snapshot["review_version"] == 1
    assert len(snapshot["business_result"]["requirements"]) == 6
    assert len(snapshot["business_result"]["evidences"]) == 5
    action = snapshot["proposed_action"]
    assert action["document_status"] == "DRAFT"
    assert action["source_type"] == "mock"
    assert ledger.get(action["operation_id"]) is None
    actual = graph.get_state(config())
    assert actual.values["review_snapshot"] == snapshot
    assert actual.next == ("human_review",)
    assert any(task.interrupts for task in actual.tasks)
    assert products(tmp_path) == []


def test_same_thread_continuity_and_start_cannot_replace_task(graph):
    pending = begin(graph)
    completed = resume_review(graph, "thread-a", response(pending))
    persisted = graph.get_state(config()).values
    assert completed["status"] == "completed"
    assert persisted["run_id"] == pending["run_id"]
    assert persisted["business_result"] == pending["business_result"]
    with pytest.raises((ValueError, RuntimeError)):
        begin(graph)


def test_threads_are_isolated_even_using_one_checkpointer(graph):
    first = begin(graph)
    assert not graph.get_state(config("thread-b")).values
    second = start_review(
        graph, "thread-b", requirements("MOCK-SW-24"), evidences=complete_evidence("MOCK-SW-24")
    )
    assert first["business_result"]["overall_status"] == "FC"
    assert second["business_result"]["overall_status"] == "NC"
    assert first["run_id"] != second["run_id"]
    assert graph.get_state(config()).values["review_snapshot"] == first["review_snapshot"]
    assert (
        graph.get_state(config("thread-b")).values["review_snapshot"] == second["review_snapshot"]
    )


def test_fresh_memory_saver_cannot_recover_old_state(ledger):
    old = build_review_graph(InMemorySaver(), ledger)
    begin(old)
    fresh = build_review_graph(InMemorySaver(), ledger)
    assert not fresh.get_state(config()).values


def test_sqlite_checkpoint_survives_connection_close(ledger, tmp_path):
    db = tmp_path / "runtime" / "checkpoints.sqlite"
    with SqliteSaver.from_conn_string(str(db)) as saver:
        saver.setup()
        graph = build_review_graph(saver, ledger)
        pending = begin(graph)
        assert saver.get_tuple(config()) is not None
    with SqliteSaver.from_conn_string(str(db)) as saver:
        graph = build_review_graph(saver, ledger)
        restored = graph.get_state(config())
        assert restored.values["review_snapshot"] == pending["review_snapshot"]
        assert restored.next == ("human_review",)
        completed = resume_review(graph, "thread-a", response(pending))
        assert completed["status"] == "completed"
    # Context exit releases the actual SQLite connection, not just a Python reference.
    with pytest.raises(Exception):
        saver.conn.execute("SELECT 1")


def test_approve_publishes_one_mock_draft_with_review_and_ledger(graph, ledger, tmp_path):
    pending = begin(graph)
    result = resume_review(graph, "thread-a", response(pending, comment="MOCK checked locally"))
    assert result["status"] == "completed"
    assert result["business_result"]["overall_status"] == "FC"
    files = products(tmp_path)
    assert len(files) == 1
    document = json.loads(files[0].read_text(encoding="utf-8"))
    assert "DRAFT" in json.dumps(document)
    assert "mock" in json.dumps(document)
    assert pending["review_snapshot"]["review_id"] in json.dumps(document)
    op = result["operation_result"]
    assert Path(op["path"]) == files[0]
    assert op["status"] == "completed"
    assert ledger.get(op["operation_id"])["status"] == "completed"


def test_reject_preserves_business_conclusion_without_file(graph, tmp_path):
    pending = begin(graph)
    rejected = resume_review(graph, "thread-a", response(pending, "reject"))
    assert rejected["status"] == "rejected"
    assert rejected["business_result"] == pending["business_result"]
    assert products(tmp_path) == []


def test_modify_revalidates_and_requires_a_new_approval(graph, tmp_path):
    pending = begin(graph)
    changed = requirements()
    changed[1] = dict(changed[1], expected_value=96)
    modified = resume_review(
        graph, "thread-a", response(pending, "modify", modification={"requirements": changed})
    )
    assert modified["status"] == "awaiting_review"
    assert modified["business_result"]["overall_status"] == "NC"
    old, new = pending["review_snapshot"], modified["review_snapshot"]
    assert new["review_version"] == old["review_version"] + 1
    assert new["review_id"] != old["review_id"]
    assert new["snapshot_digest"] != old["snapshot_digest"]
    assert new["proposed_action"]["operation_id"] != old["proposed_action"]["operation_id"]
    assert str(old["review_version"]) in modified["review_history"]
    assert str(new["review_version"]) in modified["review_history"]
    assert products(tmp_path) == []
    approved = resume_review(graph, "thread-a", response(modified))
    assert approved["status"] == "completed"
    assert len(products(tmp_path)) == 1


def test_modify_configuration_runs_applicability_validation(graph, tmp_path):
    evidence = complete_evidence()
    evidence[3] = dict(evidence[3], applicable_conditions={"module": "installed"})
    pending = start_review(graph, "thread-a", requirements(), evidences=evidence)
    assert pending["business_result"]["overall_status"] == "PENDING"
    changed = resume_review(
        graph,
        "thread-a",
        response(pending, "modify", modification={"configuration": {"module": "installed"}}),
    )
    assert changed["business_result"]["overall_status"] == "FC"
    assert changed["status"] == "awaiting_review"
    assert products(tmp_path) == []


def test_old_review_cannot_approve_modified_snapshot(graph, tmp_path):
    pending = begin(graph)
    changed = complete_evidence()
    changed[0] = dict(changed[0], actual_value=24)
    modified = resume_review(
        graph, "thread-a", response(pending, "modify", modification={"evidences": changed})
    )
    assert modified["review_snapshot"]["review_version"] == 2
    with pytest.raises((ValueError, RuntimeError)):
        resume_review(graph, "thread-a", response(pending))
    assert products(tmp_path) == []


@pytest.mark.parametrize(
    "update",
    [
        {"action": "delete"},
        {"review_version": True},
        {"review_version": "1"},
        {"review_version": 999},
        {"review_id": "old-review"},
        {"snapshot_digest": "different-digest"},
        {"unknown_field": "unexpected"},
        {"modification": {"configuration": {"module": "installed"}}},
    ],
)
def test_invalid_or_stale_direct_resume_fails_closed(graph, tmp_path, update):
    pending = begin(graph)
    failed = graph.invoke(Command(resume=response(pending, **update)), config())
    assert failed["status"] == "failed"
    assert failed.get("error_type")
    assert products(tmp_path) == []


def test_invalid_modified_business_data_is_not_approved(graph, tmp_path):
    pending = begin(graph)
    invalid = requirements()
    invalid[1] = dict(invalid[1], expected_value=True)
    state = graph.invoke(
        Command(resume=response(pending, "modify", modification={"requirements": invalid})),
        config(),
    )
    assert state["status"] == "failed"
    assert products(tmp_path) == []


def test_tampered_review_snapshot_fails_digest_check(graph, tmp_path):
    pending = begin(graph)
    tampered = deepcopy(pending["review_snapshot"])
    tampered["business_result"]["overall_status"] = "NC"
    graph.update_state(config(), {"review_snapshot": tampered})
    with pytest.raises((ValueError, RuntimeError)):
        resume_review(graph, "thread-a", response(pending))
    assert products(tmp_path) == []


def test_execution_rechecks_actual_input_matches_approved_snapshot(graph, tmp_path):
    pending = begin(graph)
    changed = requirements()
    changed[1] = dict(changed[1], expected_value=96)
    # Exercise the separate protected node after approval validation, simulating
    # a trusted application's accidental state mutation before execution.
    graph.update_state(
        config(),
        {
            "status": "approved",
            "approval": response(pending),
            "requirement_input": changed,
        },
        as_node="validate_review",
    )
    failed = graph.invoke(None, config())
    assert failed["status"] == "failed"
    assert failed["error_type"].startswith("protected_execution:")
    assert products(tmp_path) == []


def test_repeat_approval_and_command_do_not_create_or_rewrite_output(graph, tmp_path):
    pending = begin(graph)
    payload = response(pending)
    completed = resume_review(graph, "thread-a", payload)
    output = products(tmp_path)[0]
    original_bytes, mtime = output.read_bytes(), output.stat().st_mtime_ns
    repeated = resume_review(graph, "thread-a", payload)
    direct = graph.invoke(Command(resume=payload), config())
    assert repeated["operation_result"] == completed["operation_result"]
    assert direct["status"] == "completed"
    assert products(tmp_path) == [output]
    assert output.read_bytes() == original_bytes
    assert output.stat().st_mtime_ns == mtime


def test_completed_task_rejects_different_response(graph, tmp_path):
    pending = begin(graph)
    resume_review(graph, "thread-a", response(pending))
    with pytest.raises((ValueError, RuntimeError)):
        resume_review(graph, "thread-a", response(pending, "reject"))
    assert len(products(tmp_path)) == 1


@pytest.mark.parametrize("damage", ["deleted", "tampered"])
def test_repeated_approval_rejects_damaged_completed_artifact(graph, tmp_path, damage):
    pending = begin(graph)
    payload = response(pending)
    resume_review(graph, "thread-a", payload)
    artifact = products(tmp_path)[0]
    if damage == "deleted":
        artifact.unlink()
    else:
        artifact.write_text("different user contents", encoding="utf-8")
    with pytest.raises((ValueError, RuntimeError)):
        resume_review(graph, "thread-a", payload)
    if damage == "deleted":
        assert not artifact.exists()
        assert products(tmp_path) == []
    else:
        assert artifact.read_text(encoding="utf-8") == "different user contents"
        assert products(tmp_path) == [artifact]


def test_repeat_operation_uses_persistent_record_after_reopening(tmp_path):
    db = tmp_path / "runtime" / "operations.sqlite"
    output_root = tmp_path / "outputs" / "phase05"
    db.parent.mkdir()
    target = output_root / "repeat-op.json"
    payload = {"document_status": "DRAFT", "source_type": "mock", "value": 48}
    with OperationLedger(db, output_root) as ledger:
        first = ledger.execute("repeat-op", payload, target)
    before = target.read_bytes(), target.stat().st_mtime_ns
    with OperationLedger(db, output_root) as ledger:
        second = ledger.execute("repeat-op", payload, target)
        assert second["reused"] is True
        assert second["sha256"] == first["sha256"]
        assert ledger.get("repeat-op")["status"] == "completed"
    assert (target.read_bytes(), target.stat().st_mtime_ns) == before
    assert products(tmp_path) == [target]


@pytest.mark.parametrize("kind", ["traversal", "absolute", "symlink"])
def test_operation_blocks_output_path_escape(ledger, tmp_path, kind):
    root = tmp_path / "outputs" / "phase05"
    if kind == "traversal":
        target = root / ".." / "outside.json"
    elif kind == "absolute":
        target = tmp_path / "outside.json"
    else:
        outside = tmp_path / "outside"
        outside.mkdir()
        root.mkdir(parents=True, exist_ok=True)
        link = root / "link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                pytest.skip("OS does not permit creating directory symlinks")
            # NTFS directory junction creation does not require Developer Mode.
            # Both explicitly named targets stay within this test's temp root.
            assert link.is_relative_to(tmp_path) and outside.is_relative_to(tmp_path)
            process = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
                capture_output=True,
                timeout=10,
            )
            assert process.returncode == 0, process.stderr
        target = link / "escape.json"
    with pytest.raises((ValueError, RuntimeError, PermissionError)):
        ledger.execute("bad-path", {"source_type": "mock"}, target)
    assert not target.exists()
    assert not (tmp_path / "outside.json").exists()


def test_existing_unknown_file_is_not_overwritten(ledger, tmp_path):
    target = tmp_path / "outputs" / "phase05" / "existing.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("user-owned contents", encoding="utf-8")
    with pytest.raises((ValueError, RuntimeError, FileExistsError)):
        ledger.execute("existing", {"source_type": "mock"}, target)
    assert target.read_text(encoding="utf-8") == "user-owned contents"


def test_same_operation_id_cannot_change_payload_or_target(ledger, tmp_path):
    target = tmp_path / "outputs" / "phase05" / "stable.json"
    first = ledger.execute("stable", {"source_type": "mock", "count": 48}, target)
    with pytest.raises((ValueError, RuntimeError)):
        ledger.execute("stable", {"source_type": "mock", "count": 24}, target)
    with pytest.raises((ValueError, RuntimeError)):
        ledger.execute("stable", {"source_type": "mock", "count": 48}, target.with_name("new.json"))
    assert ledger.get("stable")["status"] == "completed"
    assert first["sha256"]
    assert products(tmp_path) == [target]


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "examples" / "phase05_checkpoint_hitl.py"


def run_cli(project_root, *args):
    env = {k: v for k, v in os.environ.items() if k not in ("GEMINI_API_KEY", "GOOGLE_API_KEY")}
    env["PYTHONIOENCODING"] = "ascii"
    process = subprocess.Popen(
        [sys.executable, str(CLI), "--project-root", str(project_root), *args],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="ascii",
    )
    stdout, stderr = process.communicate(timeout=30)
    assert process.returncode == 0, f"{stdout}\n{stderr}"
    return json.loads(stdout.splitlines()[-1]), process.pid


def test_real_independent_processes_restore_and_resume_sqlite_checkpoint(tmp_path):
    pending, initial_pid = run_cli(tmp_path, "start", "--thread-id", "restart-demo")
    restored, status_pid = run_cli(tmp_path, "status", "--thread-id", "restart-demo")
    assert status_pid != initial_pid
    assert restored["status"] == "awaiting_review"
    assert restored["review_snapshot"] == pending["review_snapshot"]
    snapshot = restored["review_snapshot"]
    arguments = (
        "resume",
        "--thread-id",
        "restart-demo",
        "--action",
        "approve",
        "--review-id",
        snapshot["review_id"],
        "--review-version",
        str(snapshot["review_version"]),
        "--snapshot-digest",
        snapshot["snapshot_digest"],
    )
    completed, resume_pid = run_cli(tmp_path, *arguments)
    assert resume_pid not in (initial_pid, status_pid)
    assert completed["status"] == "completed"
    assert completed["operation_result"]["status"] == "completed"
    files = products(tmp_path)
    assert len(files) == 1
    before = files[0].read_bytes(), files[0].stat().st_mtime_ns
    repeated, _ = run_cli(tmp_path, *arguments)
    assert repeated["status"] == "completed"
    assert (files[0].read_bytes(), files[0].stat().st_mtime_ns) == before
    assert len(products(tmp_path)) == 1
    assert (tmp_path / "runtime" / "phase05" / "checkpoints.sqlite").is_file()
    assert (tmp_path / "runtime" / "phase05" / "operations.sqlite").is_file()


def test_process_exit_after_publish_recovers_real_file_and_unfinished_ledger(tmp_path):
    db = tmp_path / "runtime" / "operations.sqlite"
    db.parent.mkdir()
    root = tmp_path / "outputs" / "phase05"
    target = root / "crash-op.json"
    program = (
        "import os,sys; from pathlib import Path; "
        "from agent_demo.persistence.operations import OperationLedger; "
        "ledger=OperationLedger(Path(sys.argv[1]),Path(sys.argv[2])); "
        "ledger.execute('crash-op',{'source_type':'mock','document_status':'DRAFT'},"
        "Path(sys.argv[3]),after_publish=lambda:os._exit(23))"
    )
    process = subprocess.run(
        [sys.executable, "-c", program, str(db), str(root), str(target)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert process.returncode == 23, process.stderr
    assert target.is_file()
    original = target.read_bytes(), target.stat().st_mtime_ns
    with OperationLedger(db, root) as ledger:
        assert ledger.get("crash-op")["status"] != "completed"
        recovered = ledger.execute(
            "crash-op", {"source_type": "mock", "document_status": "DRAFT"}, target
        )
        assert recovered["status"] == "completed"
        assert recovered["reused"] is True
        assert ledger.get("crash-op")["status"] == "completed"
    assert (target.read_bytes(), target.stat().st_mtime_ns) == original
    assert products(tmp_path) == [target]


def test_graph_process_crash_after_publish_restores_approved_execution(tmp_path):
    pending, _ = run_cli(tmp_path, "start", "--thread-id", "crash-graph")
    snapshot = pending["review_snapshot"]
    program = """
import os, sys
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver
from agent_demo.graphs.review_graph import build_review_graph, resume_review
from agent_demo.persistence.operations import OperationLedger
root = Path(sys.argv[1])
runtime = root / 'runtime' / 'phase05'
with OperationLedger(runtime / 'operations.sqlite', root / 'outputs' / 'phase05') as ledger:
    with SqliteSaver.from_conn_string(str(runtime / 'checkpoints.sqlite')) as saver:
        graph = build_review_graph(saver, ledger, after_publish=lambda: os._exit(24))
        state = graph.get_state({'configurable': {'thread_id': 'crash-graph'}}).values
        snapshot = state['review_snapshot']
        payload = dict(action='approve', review_id=snapshot['review_id'],
                       review_version=snapshot['review_version'],
                       snapshot_digest=snapshot['snapshot_digest'])
        resume_review(graph, 'crash-graph', payload)
"""
    crashed = subprocess.run(
        [sys.executable, "-c", program, str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert crashed.returncode == 24, crashed.stderr
    files = products(tmp_path)
    assert len(files) == 1
    original = files[0].read_bytes(), files[0].stat().st_mtime_ns
    restored, _ = run_cli(tmp_path, "status", "--thread-id", "crash-graph")
    assert restored["status"] == "approved"
    completed, _ = run_cli(
        tmp_path,
        "resume",
        "--thread-id",
        "crash-graph",
        "--action",
        "approve",
        "--review-id",
        snapshot["review_id"],
        "--review-version",
        str(snapshot["review_version"]),
        "--snapshot-digest",
        snapshot["snapshot_digest"],
    )
    assert completed["status"] == "completed"
    assert completed["operation_result"]["reused"] is True
    assert products(tmp_path) == files
    assert (files[0].read_bytes(), files[0].stat().st_mtime_ns) == original


def test_memory_checkpoint_is_lost_in_a_new_independent_process(tmp_path):
    program = """
import json, os, sys
from pathlib import Path
from langgraph.checkpoint.memory import InMemorySaver
from agent_demo.domain.mock_cases import requirements, complete_evidence
from agent_demo.graphs.review_graph import build_review_graph, start_review
from agent_demo.persistence.operations import OperationLedger
root = Path(sys.argv[1])
with OperationLedger(
    root / 'runtime' / 'operations.sqlite', root / 'outputs' / 'phase05'
) as ledger:
    graph = build_review_graph(InMemorySaver(), ledger)
    if sys.argv[2] == 'start':
        start_review(graph, 'memory-only', requirements(), evidences=complete_evidence())
    state = graph.get_state({'configurable': {'thread_id': 'memory-only'}}).values
    print(json.dumps({'pid': os.getpid(), 'status': state.get('status'), 'has_state': bool(state)}))
"""
    observations = []
    for mode in ("start", "lookup"):
        process = subprocess.run(
            [sys.executable, "-c", program, str(tmp_path), mode],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert process.returncode == 0, process.stderr
        observations.append(json.loads(process.stdout))
    assert observations[0]["pid"] != observations[1]["pid"]
    assert observations[0]["status"] == "awaiting_review"
    assert observations[0]["has_state"] is True
    assert observations[1]["has_state"] is False
    assert observations[1]["status"] is None
    assert products(tmp_path) == []


def test_business_error_ends_before_review_or_protected_execution(graph, tmp_path):
    invalid = requirements()
    invalid[1] = dict(invalid[1], expected_value=True)
    failed = start_review(graph, "business-error", invalid, evidences=complete_evidence())
    assert failed["status"] == "failed"
    assert failed["error_type"] == "business_execution_error"
    assert failed["business_result"]["overall_status"] == "ERROR"
    assert failed["business_result"]["errors"]
    assert "review_snapshot" not in failed
    assert "operation_result" not in failed
    checkpoint = graph.get_state(config("business-error"))
    assert checkpoint.next == ()
    assert not any(task.interrupts for task in checkpoint.tasks)
    assert products(tmp_path) == []


def test_cross_thread_store_experiment_and_explicit_namespace_grants():
    from langgraph.store.memory import InMemoryStore

    observed = run_store_demo()
    assert observed["thread_a_note"] == "MOCK note from A"
    assert observed["thread_b_isolated"] is True
    assert observed["fresh_saver_has_no_state"] is True
    assert observed["authorized_thread_b_store"]["source_type"] == "mock"
    assert observed["unauthorized_denied"] is True
    store = InMemoryStore()
    allowed = ("test-project", "authorized-mock")
    grants = {allowed}
    item = {"source_type": "mock", "note": "shared only by explicit grant"}
    namespace_access(store, allowed, grants, value=item)
    assert namespace_access(store, allowed, grants) == item
    with pytest.raises(PermissionError):
        namespace_access(store, ("other-project", "authorized-mock"), grants, value=item)
    assert store.get(("other-project", "authorized-mock"), "mock-note") is None


def test_phase4_remains_uninterrupted_and_inputs_not_mutated():
    reqs, evidence = requirements(), complete_evidence()
    before = deepcopy((reqs, evidence))
    result = run_workflow(reqs, evidences=evidence)
    assert result.overall_status == "FC"
    assert result.workflow_status == "completed"
    assert (reqs, evidence) == before
    assert all(item.review_status == "not_reviewed" for item in result.decisions)
