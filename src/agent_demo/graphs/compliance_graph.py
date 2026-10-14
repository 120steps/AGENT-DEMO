"""Sequential explicit business graph. No LLM, RAG, persistence or device access."""

import hashlib
import operator
from decimal import Decimal
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from agent_demo.domain.decisions import Decision, WorkflowResult
from agent_demo.domain.evidence import Evidence
from agent_demo.domain.requirements import Requirement
from agent_demo.tools import dispatch


class ComplianceState(TypedDict, total=False):
    requirement_input: list[dict]
    evidence_input: list[dict] | None
    configuration: dict[str, str]
    requirements: list[Requirement]
    evidences: dict[str, Evidence]
    validation_results: dict[str, dict]
    comparisons: dict[str, bool]
    decisions: dict[str, Decision]
    errors: dict[str, str]
    workflow_status: str
    cursor: int
    result: WorkflowResult
    evidence_mode: str
    retrieval_errors: dict[str, str]


# Default StateGraph reducers replace each field. Sequential nodes explicitly return
# copied dictionaries keyed by stable IDs, rather than append-only reducers.
UNITS = {
    "count": ("count", Decimal(1)),
    "bps": ("speed", Decimal(1)),
    "Kbps": ("speed", Decimal(1000)),
    "Mbps": ("speed", Decimal(1000000)),
    "Gbps": ("speed", Decimal(1000000000)),
    "Tbps": ("speed", Decimal(1000000000000)),
}
OPS = {">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt, "==": operator.eq}


def normalize(value, unit):
    if isinstance(value, str):
        if unit != "kind":
            raise ValueError("categorical unit must be kind")
        return "kind", value
    if value is None or unit not in UNITS:
        raise ValueError("unknown value/unit")
    dimension, factor = UNITS[unit]
    return dimension, Decimal(str(value)) * factor


def atomic_requirements(state):
    return [r for r in state["requirements"] if r.kind == "atomic"]


def current(state):
    return atomic_requirements(state)[state["cursor"]]


def load_requirements(state):
    update = dict(
        requirements=[],
        evidences={},
        validation_results={},
        comparisons={},
        decisions={},
        errors={},
        cursor=0,
        workflow_status="running",
    )
    try:
        config = state.get("configuration", {})
        if type(config) is not dict or any(
            type(k) is not str or type(v) is not str for k, v in config.items()
        ):
            raise ValueError("configuration must contain string keys and values")
        requirements = [Requirement.model_validate(r) for r in state["requirement_input"]]
        by_id = {r.id: r for r in requirements}
        if not requirements or len(by_id) != len(requirements):
            raise ValueError("empty or duplicate requirement IDs")
        for req in requirements:
            seen = {req.id}
            parent_id = req.parent_id
            while parent_id is not None:
                parent = by_id.get(parent_id)
                if (
                    parent is None
                    or parent.kind != "composite"
                    or parent.model != req.model
                    or parent_id in seen
                ):
                    raise ValueError("invalid parent hierarchy")
                seen.add(parent_id)
                parent_id = parent.parent_id
            if req.kind == "composite" and not any(r.parent_id == req.id for r in requirements):
                raise ValueError("empty composite")
        update["requirements"] = requirements
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        update["errors"] = {"input": f"requirement_validation:{type(exc).__name__}"}
    return update


def mock_spec_evidence(model, spec):
    """Only map fields actually returned by Phase 1; no invented medium/version."""
    result = []
    for attribute in ("downlink_ports", "downlink_speed", "uplink_ports", "uplink_speed"):
        value = spec[attribute]
        unit = "count"
        if attribute.endswith("speed"):
            number, unit = value.split()
            value = float(number)
        result.append(
            Evidence(
                id=f"{model}:{attribute}",
                model=model,
                attribute=attribute,
                actual_value=value,
                unit=unit,
                source_text=f"MOCK {attribute}={spec[attribute]}",
                source_document="src/agent_demo/tools/__init__.py",
                source_location=f"lookup_product_spec/{attribute}",
                source_version=None,
                source_type="mock",
            )
        )
    return result


def retrieve_evidence(state, dispatcher=dispatch):
    errors = {**state["errors"], **state.get("retrieval_errors", {})}
    evidences = {}
    try:
        if state.get("evidence_mode") == "real_rag" and state.get("evidence_input") is None:
            items = []
        elif state.get("evidence_input") is not None:
            items = [Evidence.model_validate(e) for e in state["evidence_input"]]
        else:
            items = []
            for model in sorted({r.model for r in atomic_requirements(state)}):
                try:
                    response = dispatcher("lookup_product_spec", {"model": model})
                    if response["status"] != "ok":
                        errors[model] = "tool_execution_failed"
                    elif response["result"]["status"] == "ok":
                        items.extend(mock_spec_evidence(model, response["result"]))
                except Exception as exc:
                    errors[model] = f"tool_execution_failed:{type(exc).__name__}"
        for item in items:
            if state.get("evidence_mode", "mock") != item.source_type:
                raise ValueError("MOCK and real evidence must not be mixed")
            if item.id in evidences:
                raise ValueError("duplicate evidence ID")
            evidences[item.id] = item
    except (ValidationError, ValueError, TypeError, KeyError) as exc:
        errors["evidence_input"] = f"evidence_validation:{type(exc).__name__}"
        evidences = {}
    return {"evidences": evidences, "errors": errors}


def validate_evidence(state):
    req = current(state)
    validation = {"status": "missing", "ids": [], "missing": [], "conflicts": []}
    if req.model in state["errors"] or "evidence_input" in state["errors"]:
        validation["status"] = "error"
    else:
        config = state.get("configuration", {})
        if any(config.get(k) != v for k, v in req.applicable_conditions.items()):
            validation["missing"].append("requirement applicability/configuration unconfirmed")
        else:
            values = []
            for evidence in state["evidences"].values():
                if evidence.model != req.model or evidence.attribute != req.attribute:
                    continue
                if evidence.source_type == "real_rag":
                    proof_metadata = evidence.metadata or {}
                    if (
                        proof_metadata.get("verified_chunk_sha256")
                        != hashlib.sha256((evidence.source_text or "").encode()).hexdigest()
                    ):
                        validation["missing"].append(
                            f"{evidence.id}: verified chunk content changed"
                        )
                        continue
                    if not all(
                        (
                            evidence.document_id,
                            evidence.source_version,
                            evidence.chunk_id is not None,
                            evidence.page is not None,
                            evidence.page_number_semantics == "pdf_physical_1_based",
                            evidence.origin_verified,
                            evidence.document_hash,
                            evidence.extraction_method == "deterministic_spec_line",
                        )
                    ):
                        validation["missing"].append(f"{evidence.id}: real provenance unverified")
                        continue
                    # Re-check the narrow extraction grammar rather than trusting a
                    # caller/LLM-supplied numeric value or extraction flag.
                    from agent_demo.integrations.rag_evidence import extract_spec_values

                    if (evidence.actual_value, evidence.unit) not in extract_spec_values(
                        evidence.source_text or "", evidence.attribute
                    ):
                        validation["missing"].append(f"{evidence.id}: unsupported numeric claim")
                        continue
                if any(config.get(k) != v for k, v in evidence.applicable_conditions.items()):
                    validation["missing"].append(
                        f"{evidence.id}: configuration unconfirmed/mismatch"
                    )
                    continue
                if not all(
                    value and value.strip()
                    for value in (
                        evidence.source_text,
                        evidence.source_document,
                        evidence.source_location,
                    )
                ):
                    validation["missing"].append(f"{evidence.id}: source incomplete")
                    continue
                try:
                    actual = normalize(evidence.actual_value, evidence.unit)
                    expected = normalize(req.expected_value, req.unit)
                    if actual[0] != expected[0]:
                        raise ValueError("incompatible dimensions")
                except ValueError:
                    validation["missing"].append(f"{evidence.id}: value/unit not comparable")
                    continue
                validation["ids"].append(evidence.id)
                values.append(actual[1])
            if values:
                # All selected evidence is applicable to this confirmed configuration.
                # Different versions do not silently authorize choosing one source.
                if len(set(values)) > 1:
                    validation["status"] = "conflict"
                    validation["conflicts"] = list(validation["ids"])
                else:
                    validation["status"] = "ready"
                    validation["missing"] = []
            elif not validation["missing"]:
                validation["missing"] = [f"no applicable evidence: {req.model}/{req.attribute}"]
    return {"validation_results": {**state["validation_results"], req.id: validation}}


def compare_requirement(state):
    req = current(state)
    evidence = state["evidences"][state["validation_results"][req.id]["ids"][0]]
    actual = normalize(evidence.actual_value, evidence.unit)[1]
    expected = normalize(req.expected_value, req.unit)[1]
    passed = OPS[req.operator](actual, expected)
    return {"comparisons": {**state["comparisons"], req.id: passed}}


def handle_error(state):
    return {"workflow_status": "failed"}


def build_decision(state):
    req = current(state)
    validation = state["validation_results"][req.id]
    status = validation["status"]
    if status == "ready":
        proposed = "FC" if state["comparisons"][req.id] else "NC"
        reason = (
            (
                "Applicable MOCK evidence satisfies rule"
                if state.get("evidence_mode", "mock") == "mock"
                else "Applicable evidence satisfies rule"
            )
            if proposed == "FC"
            else (
                "Applicable MOCK evidence proves requirement is not met"
                if state.get("evidence_mode", "mock") == "mock"
                else "Applicable evidence proves requirement is not met"
            )
        )
        evidence = state["evidences"][validation["ids"][0]]
        reason += (
            f": {req.attribute} actual={evidence.actual_value} {evidence.unit}; "
            f"required {req.operator} {req.expected_value} {req.unit}"
        )
    elif status == "error":
        proposed, reason = "ERROR", "Tool/input execution failure; not device noncompliance"
    else:
        proposed, reason = "PENDING", "Evidence missing, inapplicable or conflicting"
    decision = Decision(
        requirement_id=req.id,
        proposed_status=proposed,
        reason=reason,
        evidence_ids=validation["ids"],
        validation_result=status,
        missing_items=validation["missing"],
        conflict_items=validation["conflicts"],
    )
    return {"decisions": {**state["decisions"], req.id: decision}, "cursor": state["cursor"] + 1}


def aggregate(children, requirements):
    """Conservative MOCK policy: unknown first; mandatory failure NC, optional failure PC."""
    statuses = [d.proposed_status for d in children]
    if "ERROR" in statuses:
        return "ERROR"
    if "PENDING" in statuses:
        return "PENDING"
    if any(
        d.proposed_status == "NC" and requirements[d.requirement_id].mandatory for d in children
    ):
        return "NC"
    if "PC" in statuses:
        return "PC"
    if "NC" in statuses:
        return "PC" if "FC" in statuses else "PENDING"
    return "FC"


def finalize_result(state):
    decisions = dict(state["decisions"])
    by_id = {r.id: r for r in state["requirements"]}
    remaining = [r for r in state["requirements"] if r.kind == "composite"]
    while remaining:
        for req in list(remaining):
            child_ids = [r.id for r in state["requirements"] if r.parent_id == req.id]
            if not all(cid in decisions for cid in child_ids):
                continue
            children = [decisions[cid] for cid in child_ids]
            decisions[req.id] = Decision(
                requirement_id=req.id,
                proposed_status=aggregate(children, by_id),
                reason=(
                    "MOCK conservative composite policy: "
                    if state.get("evidence_mode", "mock") == "mock"
                    else "Conservative composite policy: "
                )
                + "; ".join(f"{d.requirement_id}={d.proposed_status}" for d in children),
                evidence_ids=sorted({eid for d in children for eid in d.evidence_ids}),
                validation_result="aggregated",
                missing_items=[item for d in children for item in d.missing_items],
                conflict_items=[item for d in children for item in d.conflict_items],
            )
            remaining.remove(req)
    roots = [decisions[r.id] for r in state["requirements"] if r.parent_id is None]
    overall = aggregate(roots, by_id) if roots else "ERROR"
    if state["errors"]:
        overall = "ERROR"
    workflow_status = "failed" if overall == "ERROR" else "completed"
    result = WorkflowResult(
        overall_status=overall,
        workflow_status=workflow_status,
        decisions=list(decisions.values()),
        errors=state["errors"],
        requirements=state["requirements"],
        evidences=list(state["evidences"].values()),
        validation_results=state["validation_results"],
        source_type=state.get("evidence_mode", "mock"),
    )
    return {"decisions": decisions, "workflow_status": workflow_status, "result": result}


def build_compliance_graph(dispatcher=dispatch):
    graph = StateGraph(ComplianceState)
    graph.add_node("load_requirements", load_requirements)
    graph.add_node("retrieve_evidence", lambda state: retrieve_evidence(state, dispatcher))
    graph.add_node("validate_evidence", validate_evidence)
    graph.add_node("compare_requirement", compare_requirement)
    graph.add_node("handle_error", handle_error)
    graph.add_node("build_decision", build_decision)
    graph.add_node("finalize_result", finalize_result)
    graph.add_edge(START, "load_requirements")
    graph.add_conditional_edges(
        "load_requirements",
        lambda s: "error" if s["errors"] else "ok",
        {"error": "finalize_result", "ok": "retrieve_evidence"},
    )
    graph.add_edge("retrieve_evidence", "validate_evidence")
    graph.add_conditional_edges(
        "validate_evidence",
        lambda s: s["validation_results"][current(s).id]["status"],
        {
            "ready": "compare_requirement",
            "missing": "build_decision",
            "conflict": "build_decision",
            "error": "handle_error",
        },
    )
    graph.add_edge("compare_requirement", "build_decision")
    graph.add_edge("handle_error", "build_decision")
    graph.add_conditional_edges(
        "build_decision",
        lambda s: "next" if s["cursor"] < len(atomic_requirements(s)) else "done",
        {"next": "validate_evidence", "done": "finalize_result"},
    )
    graph.add_edge("finalize_result", END)
    return graph.compile()


def run_workflow(
    requirements,
    *,
    evidences=None,
    configuration=None,
    dispatcher=dispatch,
    evidence_mode="mock",
    retrieval_errors=None,
):
    if evidence_mode not in {"mock", "real_rag"}:
        raise ValueError("invalid evidence mode")
    if evidence_mode == "real_rag" and evidences is None:
        evidences = []  # Never fall back to the MOCK spec tool for a real task.
    # Finite graph steps proportional to validated input size, not model decisions.
    return build_compliance_graph(dispatcher).invoke(
        {
            "requirement_input": requirements,
            "evidence_input": evidences,
            "configuration": configuration or {},
            "evidence_mode": evidence_mode,
            "retrieval_errors": retrieval_errors or {},
        },
        {"recursion_limit": max(20, 5 * len(requirements) + 10)},
    )["result"]
