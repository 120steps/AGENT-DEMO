"""Unified offline evaluation; execute existing agents, graphs, and MCP boundaries."""

import json
import os
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from agent_demo.evaluation.benchmarks import run_benchmarks
from agent_demo.evaluation.live import live_case
from agent_demo.evaluation.metrics import aggregate
from agent_demo.evaluation.models import CaseResult, EvaluationCase
from agent_demo.evaluation.report import metadata, write_report
from agent_demo.evaluation.scenarios import HANDLERS
from agent_demo.evaluation.security import compare
from agent_demo.observability import Trace


def load_cases(path):
    data = json.loads(Path(path).read_text("utf-8"))
    cases = [EvaluationCase.model_validate(row) for row in data["evaluation_cases"]]
    if not cases or len({c.case_id for c in cases}) != len(cases):
        raise ValueError("empty dataset or duplicate case IDs")
    return cases


def real_blocker(case, include_live):
    if case.execution_mode not in {"real_llm", "real_rag"}:
        return None
    if case.execution_mode == "real_llm" and not (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    ):
        return "model_credentials_missing"
    if case.execution_mode == "real_rag" and not all(
        os.getenv(k)
        for k in (
            "AGENT_DEMO_RAG_BASE_URL",
            "AGENT_DEMO_RAG_TOKEN",
            "AGENT_DEMO_RAG_BINDINGS_JSON",
            "AGENT_DEMO_RAG_TEST_QUERY",
        )
    ):
        return "safe_service_and_pdf_configuration_missing"
    if (
        case.execution_mode == "real_rag"
        and os.getenv("AGENT_DEMO_LIVE_RAG_CONFIRM_READONLY") != "1"
    ):
        return "safe_service_confirmation_required"
    if not include_live:
        return "live_opt_in_required"
    return None


def execute_cases(cases, directory, *, handlers=None, include_live=False):
    handlers = HANDLERS if handlers is None else handlers
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    trace_path = directory / "trace.jsonl"
    with trace_path.open("x", encoding="utf-8"):
        pass
    results = []
    for case in cases:
        trace = Trace(trace_path)
        started = perf_counter()
        blocker = real_blocker(case, include_live)
        if case.input.get("skip_reason"):
            results.append(
                CaseResult(
                    case.case_id,
                    case.category,
                    case.execution_mode,
                    trace.run_id,
                    "SKIPPED",
                    None,
                    0,
                    error_type="explicit_dataset_skip",
                )
            )
            trace.emit("FINAL_RESULT", status="SKIPPED", error_type="explicit_dataset_skip")
            continue
        if blocker:
            trace.emit("FINAL_RESULT", status="BLOCKED", error_type=blocker)
            results.append(
                CaseResult(
                    case.case_id,
                    case.category,
                    case.execution_mode,
                    trace.run_id,
                    "BLOCKED",
                    None,
                    0,
                    error_type=blocker,
                )
            )
            continue
        trace.emit("USER_REQUEST", layer=case.category, status="started")
        try:
            with TemporaryDirectory(prefix="agent-demo-phase08-") as temporary:
                handler = (
                    live_case
                    if case.execution_mode.startswith("real_")
                    else handlers[case.category]
                )
                actual = handler(case, trace, Path(temporary))
            mismatches = compare(case, actual)
            outcome, error = ("FAIL" if mismatches else "PASS"), None
        except TimeoutError:
            actual, mismatches, outcome, error = None, [], "TIMEOUT", "TimeoutError"
        except Exception as exc:
            actual, mismatches, outcome, error = None, [], "ENV_ERROR", type(exc).__name__
        elapsed = (perf_counter() - started) * 1000
        trace.emit(
            "FINAL_RESULT",
            layer=case.category,
            status=outcome,
            elapsed_ms=elapsed,
            error_type=error,
        )
        results.append(
            CaseResult(
                case.case_id,
                case.category,
                case.execution_mode,
                trace.run_id,
                outcome,
                actual,
                elapsed,
                mismatches,
                error,
            )
        )
    return results


def run_evaluation(
    dataset, directory, *, include_live=False, benchmarks=True, save_baseline=None, selected=None
):
    cases = load_cases(dataset)
    if selected:
        selected = set(selected)
        if not selected <= {case.case_id for case in cases}:
            raise ValueError("unknown replay case ID")
        cases = [case for case in cases if case.case_id in selected]
    results = execute_cases(cases, directory, include_live=include_live)
    report = {
        "metadata": metadata(dataset, Path(__file__).resolve().parents[3]),
        "metrics": aggregate(results, cases),
        "results": [asdict(r) for r in results],
        "benchmarks": None,
    }
    report["metadata"]["execution_modes"] = sorted({r.execution_mode for r in results})
    report["metadata"]["real_model_runs"] = [
        {"case_id": r.case_id, "outcome": r.outcome, "metadata": r.actual.facts}
        for r in results
        if r.execution_mode == "real_llm" and r.actual is not None
    ]
    if report["metadata"]["real_model_runs"]:
        report["metadata"]["model_provider"] = "mixed; see real_model_runs"
        report["metadata"]["model_id"] = "see real_model_runs"
    if benchmarks:
        try:
            report["benchmarks"] = run_benchmarks()
        except Exception as exc:
            report["benchmarks"] = {"status": "ENV_ERROR", "error_type": type(exc).__name__}
            report["metrics"]["hard_gate_passed"] = False
    write_report(report, directory, baseline_root=save_baseline)
    return report
