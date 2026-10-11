"""Offline tests exercise real compiled StateGraphs and MOCK evidence only."""

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_demo.domain.evidence import Evidence
from agent_demo.domain.mock_cases import complete_evidence, requirements, scenarios
from agent_demo.domain.requirements import Requirement
from agent_demo.graphs.compliance_graph import (
    build_compliance_graph,
    load_requirements,
    run_workflow,
    validate_evidence,
)


def leaf(attribute="downlink_ports", **updates):
    req = next(r for r in requirements() if r.get("attribute") == attribute)
    return [dict(req, parent_id=None, **updates)]


@pytest.mark.parametrize(
    "name,status",
    [
        ("fully_satisfied", "FC"),
        ("insufficient_count", "NC"),
        ("optional_module_unconfirmed", "PENDING"),
        ("missing_evidence", "PENDING"),
        ("conflicting_evidence", "PENDING"),
    ],
)
def test_five_mock_scenarios(name, status):
    reqs, evidence = scenarios()[name]
    result = run_workflow(reqs, evidences=evidence)
    assert result.overall_status == status
    assert result.workflow_status == "completed"
    assert len(result.decisions) == 6
    assert result.decisions[-1].requirement_id == "ports"
    assert result.source_type == "mock"


def test_actual_dispatcher_fields_and_missing_medium():
    assert run_workflow(leaf()).overall_status == "FC"
    result = run_workflow(requirements())
    assert result.overall_status == "PENDING"
    medium = next(d for d in result.decisions if d.requirement_id == "downlink_medium")
    assert medium.missing_items


@pytest.mark.parametrize(
    "op,expected,status",
    [
        (">=", 48, "FC"),
        (">", 48, "NC"),
        ("<=", 48, "FC"),
        ("<", 49, "FC"),
        ("==", 48, "FC"),
        ("==", 24, "NC"),
    ],
)
def test_numeric_operators(op, expected, status):
    assert run_workflow(leaf(operator=op, expected_value=expected)).overall_status == status


def test_unit_conversion_and_equivalent_sources_not_conflict():
    evidence = complete_evidence()
    speed = next(e for e in evidence if e["attribute"] == "uplink_speed")
    evidence.append(dict(speed, id="Mbps-equivalent", actual_value=10000, unit="Mbps"))
    assert (
        run_workflow(
            leaf("uplink_speed", expected_value=10000, unit="Mbps"), evidences=evidence
        ).overall_status
        == "FC"
    )


@pytest.mark.parametrize(
    "change",
    [
        {"model": "MOCK-SW-24"},
        {"attribute": "unknown"},
        {"unit": "count"},
        {"unit": "unknown"},
        {"actual_value": None},
        {"source_document": None},
        {"source_location": None},
        {"source_text": None},
        {"source_text": "   "},
    ],
)
def test_inapplicable_unknown_evidence_never_nc(change):
    evidence = next(e for e in complete_evidence() if e["attribute"] == "uplink_speed")
    result = run_workflow(leaf("uplink_speed"), evidences=[dict(evidence, **change)])
    assert result.overall_status == "PENDING"


def test_module_confirmation_and_requirement_conditions():
    reqs, evidence = scenarios()["optional_module_unconfirmed"]
    assert (
        run_workflow(
            reqs, evidences=evidence, configuration={"uplink_module": "installed"}
        ).overall_status
        == "FC"
    )
    req = leaf(applicable_conditions={"mode": "active"})
    assert run_workflow(req).overall_status == "PENDING"
    assert run_workflow(req, configuration={"mode": "active"}).overall_status == "FC"


def test_unknown_overrides_known_failure_in_composite():
    evidence = complete_evidence("MOCK-SW-24")
    evidence = [e for e in evidence if e["attribute"] != "uplink_ports"]
    result = run_workflow(requirements("MOCK-SW-24"), evidences=evidence)
    assert result.overall_status == "PENDING"
    assert any(d.proposed_status == "NC" for d in result.decisions)


def test_known_optional_limitation_pc():
    reqs = requirements("MOCK-SW-24")
    reqs = [dict(r, mandatory=False) if r["id"] == "downlink_ports" else r for r in reqs]
    result = run_workflow(reqs, evidences=complete_evidence("MOCK-SW-24"))
    assert result.overall_status == "PC"


def test_nested_composite_preserves_ancestry():
    reqs = requirements()
    reqs[0] = dict(reqs[0], parent_id="root")
    reqs.append(dict(reqs[0], id="root", parent_id=None))
    result = run_workflow(reqs, evidences=complete_evidence())
    assert result.overall_status == "FC"
    assert len(result.decisions) == 7


@pytest.mark.parametrize(
    "mutator",
    [
        lambda r: [],
        lambda r: r + [r[1]],
        lambda r: [dict(r[1], parent_id="absent")],
        lambda r: [dict(r[0], parent_id="ports"), *r[1:]],
        lambda r: [r[0]],
        lambda r: leaf(operator="!="),
        lambda r: leaf(expected_value=True),
        lambda r: leaf(expected_value=float("inf")),
        lambda r: leaf(model="../../secret"),
    ],
)
def test_bad_input_is_workflow_error(mutator):
    result = run_workflow(mutator(requirements()))
    assert result.overall_status == "ERROR"
    assert result.workflow_status == "failed"
    assert result.errors


def test_mock_only_evidence_and_duplicate_ids():
    evidence = complete_evidence()
    with pytest.raises(ValidationError):
        Evidence.model_validate(dict(evidence[0], source_type="real"))
    for bad in ([dict(evidence[0], actual_value=True)], evidence + [evidence[0]]):
        assert run_workflow(leaf(), evidences=bad).overall_status == "ERROR"


@pytest.mark.parametrize("raises", [True, False])
def test_tool_failure_error_not_nc_and_all_leaves_processed(raises):
    def failed_dispatcher(name, arguments):
        assert name == "lookup_product_spec"
        if raises:
            raise RuntimeError("private diagnostic text")
        return {"status": "error"}

    result = run_workflow(requirements(), dispatcher=failed_dispatcher)
    assert result.overall_status == "ERROR"
    assert len(result.decisions) == 6
    assert all(d.proposed_status == "ERROR" for d in result.decisions)
    assert "private diagnostic text" not in result.model_dump_json()


def test_node_updates_do_not_mutate_and_default_reducer_replaces():
    initial = {"requirement_input": leaf(), "evidence_input": complete_evidence()}
    snapshot = deepcopy(initial)
    update = load_requirements(initial)
    assert initial == snapshot
    from agent_demo.graphs.compliance_graph import retrieve_evidence

    state = {**initial, **update, **retrieve_evidence({**initial, **update})}
    before = deepcopy(state)
    delta = validate_evidence(state)
    assert state == before
    assert delta["validation_results"] is not state["validation_results"]
    graph = build_compliance_graph()
    first = graph.invoke(initial)
    repeated = graph.invoke(first)
    assert first["result"] == repeated["result"]
    assert len(repeated["decisions"]) == 1
    # A new run explicitly resets previous maps; no append reducer pollution.
    changed = graph.invoke(
        {**first, "requirement_input": leaf("uplink_ports"), "evidence_input": []}
    )
    assert set(changed["decisions"]) == {"uplink_ports"}
    assert changed["result"].overall_status == "PENDING"


@pytest.mark.parametrize(
    "case,compare,error",
    [
        ("fully_satisfied", True, False),
        ("missing_evidence", False, False),
        ("conflicting_evidence", True, False),
        ("tool_error", False, True),
    ],
)
def test_real_graph_conditional_paths(case, compare, error):
    if case == "tool_error":
        reqs, evidence = requirements(), None
        graph = build_compliance_graph(lambda *args: {"status": "error"})
    else:
        reqs, evidence = scenarios()[case]
        graph = build_compliance_graph()
    updates = list(
        graph.stream(
            {"requirement_input": reqs, "evidence_input": evidence},
            {"recursion_limit": 50},
            stream_mode="updates",
        )
    )
    names = [next(iter(update)) for update in updates]
    assert ("compare_requirement" in names) is compare
    assert ("handle_error" in names) is error
    assert names.count("build_decision") == 5
    assert names[-1] == "finalize_result"


def test_immutable_requirement_and_manual_decomposition():
    req = Requirement.model_validate(requirements()[1])
    assert req.parent_id == "ports" and req.original_text == requirements()[0]["original_text"]
    with pytest.raises(ValidationError):
        req.expected_value = 0


def test_invalid_configuration_is_error():
    assert run_workflow(leaf(), configuration={"module": True}).overall_status == "ERROR"


def test_optional_only_failure_cannot_prove_mandatory_noncompliance():
    result = run_workflow(leaf(expected_value=99, mandatory=False))
    assert result.decisions[0].proposed_status == "NC"
    assert result.overall_status == "PENDING"


def test_conflicting_leaf_skips_numeric_comparison_but_others_continue():
    reqs, evidence = scenarios()["conflicting_evidence"]
    updates = list(
        build_compliance_graph().stream(
            {"requirement_input": reqs, "evidence_input": evidence},
            {"recursion_limit": 50},
            stream_mode="updates",
        )
    )
    comparisons = [
        u["compare_requirement"]["comparisons"] for u in updates if "compare_requirement" in u
    ]
    assert len(comparisons) == 4
    assert all("downlink_ports" not in c for c in comparisons)


def test_result_retains_traceable_inputs_evidence_and_validation():
    result = run_workflow(requirements(), evidences=complete_evidence())
    data = result.model_dump(mode="json")
    assert len(data["requirements"]) == 6
    by_id = {e["id"]: e for e in data["evidences"]}
    for decision in data["decisions"]:
        assert all(eid in by_id for eid in decision["evidence_ids"])
    assert by_id["MOCK-SW-48:downlink_ports"]["source_version"] is None
    assert data["validation_results"]["downlink_ports"]["status"] == "ready"


def test_demo_runs_on_ascii_console_without_credentials():
    root = Path(__file__).resolve().parents[1]
    env = {k: v for k, v in os.environ.items() if k not in ("GEMINI_API_KEY", "GOOGLE_API_KEY")}
    env["PYTHONIOENCODING"] = "ascii"
    process = subprocess.run(
        [sys.executable, str(root / "examples/phase04_langgraph_workflow.py")],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="ascii",
        timeout=15,
    )
    assert process.returncode == 0, process.stderr
    results = [json.loads(line) for line in process.stdout.splitlines()]
    assert [r["overall_status"] for r in results] == ["FC", "NC", "PENDING", "PENDING", "PENDING"]
    assert results[0]["requirements"][0]["original_text"] == requirements()[0]["original_text"]
