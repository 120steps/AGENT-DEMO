"""Actual dataset execution and evaluator negative controls, with isolated artifacts."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agent_demo.evaluation.metrics import aggregate
from agent_demo.evaluation.models import CaseResult, Observation
from agent_demo.evaluation.report import write_report
from agent_demo.evaluation.runner import execute_cases, load_cases, run_evaluation
from agent_demo.observability import read_trace

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "eval/agent_test_cases.json"


@pytest.fixture(scope="module")
def evaluation(tmp_path_factory):
    directory = tmp_path_factory.mktemp("phase08-report")
    report = run_evaluation(DATASET, directory)
    return directory, report


def test_actual_all_offline_cases_and_benchmarks(evaluation):
    _, report = evaluation
    assert report["metrics"]["task"]["pass"] == 44
    assert report["metrics"]["task"]["blocked"] == 4
    assert report["metrics"]["task"]["executed"] == 44
    assert report["metrics"]["hard_gate_passed"]
    assert report["benchmarks"]["native_vs_langchain"]["samples"]
    assert len(report["benchmarks"]["python_vs_mcp"]["samples"]) == 3
    assert report["benchmarks"]["fixed_vs_agentic"]["real_pdf_citation_accuracy"] is None


def test_legacy_dataset_compatibility_and_explicit_modes():
    raw = json.loads(DATASET.read_text("utf-8"))
    assert len(raw["cases"]) == 6 and raw["live_cases"] == []
    cases = load_cases(DATASET)
    assert len(cases) == 48
    assert {c.category for c in cases} == {"tool", "compliance", "review", "rag", "mcp"}
    assert {c.execution_mode for c in cases} == {
        "offline_mock",
        "mcp_stdio",
        "mcp_memory",
        "real_llm",
        "real_rag",
    }


def test_failure_timeout_environment_error_continue(tmp_path):
    base = load_cases(DATASET)[0]
    cases = [
        base.model_copy(update={"case_id": name, "input": {"scenario": name}})
        for name in ("wrong", "timeout", "environment", "correct")
    ]

    def handler(case, trace, root):
        scenario = case.input["scenario"]
        if scenario == "timeout":
            raise TimeoutError("Bearer TEST-SECRET")
        if scenario == "environment":
            raise OSError("private API Key must not be logged")
        return Observation(
            "wrong" if scenario == "wrong" else "completed",
            facts={"executed": 1, "tool_results": [42]},
            actions=["add"],
        )

    results = execute_cases(cases, tmp_path, handlers={"tool": handler})
    assert [r.outcome for r in results] == ["FAIL", "TIMEOUT", "ENV_ERROR", "PASS"]
    assert aggregate(results, cases)["task"]["success_rate"]["denominator"] == 4
    assert "TEST-SECRET" not in (tmp_path / "trace.jsonl").read_text("utf-8")


def test_skip_and_blocked_never_enter_denominator(tmp_path):
    cases = load_cases(DATASET)
    skipped = cases[0].model_copy(
        update={"case_id": "skip-case", "input": {"skip_reason": "fixture"}}
    )
    blocked = next(c for c in cases if c.execution_mode == "real_llm")
    results = execute_cases([skipped, blocked], tmp_path)
    metrics = aggregate(results, [skipped, blocked])
    assert metrics["task"]["success_rate"]["value"] is None
    assert not metrics["hard_gate_passed"]


def test_unsupported_fc_cannot_hide_inside_high_score():
    case = load_cases(DATASET)[0].model_copy(update={"expected_status": "FC"})
    observation = Observation("FC", decisions=[{"proposed_status": "FC", "evidence_ids": []}])
    result = CaseResult(
        case.case_id, case.category, case.execution_mode, "run", "PASS", observation, 1
    )
    metrics = aggregate([result], [case])
    assert metrics["task"]["success_rate"]["value"] == 1
    assert metrics["safety"]["unsupported_fc"] == 1
    assert not metrics["hard_gate_passed"]


def test_provider_usage_and_latency_are_measured_or_unavailable(evaluation):
    _, report = evaluation
    metrics = report["metrics"]
    assert metrics["efficiency"]["token_usage"] is None
    assert metrics["efficiency"]["estimated_cost"] is None
    assert metrics["efficiency"]["model_latency_ms"] >= 0
    assert metrics["efficiency"]["tool_latency_ms"] > 0
    case = load_cases(DATASET)[0]
    actual = Observation(
        "completed", token_usage={"input_tokens": 7, "output_tokens": 2, "total_tokens": 9}
    )
    row = CaseResult(case.case_id, case.category, "real_llm", "run", "PASS", actual, 1)
    measured = aggregate([row], [case])["efficiency"]
    assert measured["token_usage"]["total_tokens"] == 9
    assert measured["estimated_cost"] is None


def test_reports_roundtrip_and_baseline_never_overwritten(evaluation, tmp_path):
    directory, report = evaluation
    assert json.loads((directory / "results.json").read_text("utf-8")) == report
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    write_report(report, tmp_path / "first", baseline_root=baseline)
    snapshot = (baseline / "phase08_results.json").read_bytes()
    with pytest.raises(FileExistsError):
        write_report(report, tmp_path / "second", baseline_root=baseline)
    assert (baseline / "phase08_results.json").read_bytes() == snapshot
    assert report["metadata"]["dataset_sha256"]
    assert report["metadata"]["git_commit"]


def test_trace_node_call_pair_and_checkpoint_correlation(evaluation):
    directory, report = evaluation
    results = {r["case_id"]: r for r in report["results"]}
    events = read_trace(directory / "trace.jsonl", results["tool-single"]["run_id"])
    request = next(e for e in events if e["event_type"] == "TOOL_CALL")
    returned = next(e for e in events if e["event_type"] == "TOOL_RESULT")
    assert request["tool_call_id"] == returned["tool_call_id"]
    graph_events = read_trace(
        directory / "trace.jsonl", results["compliance-fully-satisfied"]["run_id"]
    )
    assert any(
        e["node_name"] == "compare_requirement" and e["event_type"] == "NODE_START"
        for e in graph_events
    )
    review = read_trace(directory / "trace.jsonl", results["review-repeat-resume"]["run_id"])
    threads = {e["thread_id"] for e in review if e["thread_id"]}
    assert len(threads) == 1
    restored = read_trace(directory / "trace.jsonl", results["review-checkpoint"]["run_id"])
    assert {e["event_type"] for e in restored} >= {"CHECKPOINT_START", "CHECKPOINT_STATUS"}


def test_cli_failure_exit_and_case_replay(tmp_path):
    data = json.loads(DATASET.read_text("utf-8"))
    case = next(c for c in data["evaluation_cases"] if c["case_id"] == "tool-unknown")
    case["expected_status"] = "completed"  # evaluator must detect this deliberately wrong oracle.
    data["evaluation_cases"] = [case]
    path = tmp_path / "bad-oracle.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    run = subprocess.run(
        [
            sys.executable,
            str(ROOT / "examples/phase08_evaluation.py"),
            "--dataset",
            str(path),
            "--output",
            str(tmp_path / "result"),
            "--no-benchmarks",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert run.returncode == 1
    assert json.loads(run.stdout)["metrics"]["task"]["fail"] == 1


def test_duplicate_case_ids_rejected(tmp_path):
    case = load_cases(DATASET)[0].model_dump()
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps({"evaluation_cases": [case, case]}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(path)
