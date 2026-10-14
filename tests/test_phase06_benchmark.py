"""Offline benchmark assertions prove control paths, not real-world superiority."""

import json
from pathlib import Path

from agent_demo.evaluation.rag_benchmark import offline_benchmark


def test_offline_manifest_matches_actual_agent_graph_and_no_real_metrics_claimed():
    manifest = json.loads(
        (Path(__file__).resolve().parents[1] / "eval/agent_test_cases.json").read_text("utf-8")
    )
    result = offline_benchmark()
    expected = {case["id"]: case for case in manifest["cases"]}
    for row in result["rows"]:
        assert row["agent_calls"] == expected[row["case_id"]]["expected_agent_searches"]
        assert row["agent_status"] == expected[row["case_id"]]["expected_status"]
    assert result["verification_mode"] == "offline_mock"
    assert result["real_benchmark_status"] == "BLOCKED"
    assert result["real_document_success_rate"] is None
    assert result["real_pdf_citation_accuracy"] is None
