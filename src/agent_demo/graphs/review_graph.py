"""Checkpointed review extension reusing the complete Phase 4 business graph."""

import hashlib
import json
from copy import deepcopy
from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import ValidationError

from agent_demo.domain.reviews import ReviewResponse, ReviewSnapshot
from agent_demo.graphs.compliance_graph import run_workflow


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()


def snapshot_digest(snapshot):
    return digest({k: v for k, v in snapshot.items() if k != "snapshot_digest"})


def check_response(snapshot, response):
    for field in ("review_id", "review_version", "snapshot_digest"):
        if getattr(response, field) != snapshot[field]:
            raise ValueError("stale or mismatched review")
    if snapshot_digest(snapshot) != snapshot["snapshot_digest"]:
        raise ValueError("review snapshot changed")


class ReviewState(TypedDict, total=False):
    requirement_input: list[dict]
    evidence_input: list[dict] | None
    configuration: dict[str, str]
    run_id: str
    thread_id: str
    review_version: int
    business_result: dict
    review_snapshot: dict
    review_history: dict[str, dict]
    review_response: dict
    approval: dict | None
    status: str
    error_type: str | None
    operation_result: dict


def evaluate_requirements(state):
    # Existing compiled StateGraph performs all business validation/comparison.
    result = run_workflow(
        state["requirement_input"],
        evidences=state.get("evidence_input"),
        configuration=state.get("configuration"),
    )
    return {
        "business_result": result.model_dump(mode="json"),
        "approval": None,
        "error_type": "business_execution_error" if result.workflow_status == "failed" else None,
        "status": "failed" if result.workflow_status == "failed" else "evaluated",
    }


def build_review_graph(checkpointer, ledger, *, after_publish=None):
    def prepare_review(state):
        version = state.get("review_version", 0) + 1
        operation_id = digest(
            {
                "run": state["run_id"],
                "thread": state["thread_id"],
                "version": version,
                "result": state["business_result"],
                "configuration": state.get("configuration", {}),
                "root": str(ledger.output_root),
            }
        )
        snapshot = dict(
            run_id=state["run_id"],
            thread_id=state["thread_id"],
            review_id=digest({"operation": operation_id, "purpose": "human_review"}),
            review_version=version,
            business_result=deepcopy(state["business_result"]),
            configuration=deepcopy(state.get("configuration", {})),
            proposed_action=dict(
                kind="write_mock_soc_draft",
                operation_id=operation_id,
                target_path=str(ledger.output_root / f"{operation_id}.json"),
                document_status="DRAFT",
                source_type="mock",
            ),
        )
        snapshot["snapshot_digest"] = snapshot_digest(snapshot)
        ReviewSnapshot.model_validate(snapshot)
        return {
            "review_snapshot": snapshot,
            "review_version": version,
            "review_history": {
                **state.get("review_history", {}),
                str(version): {"snapshot": deepcopy(snapshot)},
            },
            "approval": None,
            "status": "awaiting_review",
        }

    def human_review(state):
        # No side effects here: this node restarts before interrupt on resume.
        response = interrupt(deepcopy(state["review_snapshot"]))
        return {"review_response": response}

    def validate_review(state):
        try:
            response = ReviewResponse.model_validate(state["review_response"])
            check_response(state["review_snapshot"], response)
            history = deepcopy(state["review_history"])
            history[str(state["review_version"])]["response"] = response.model_dump(
                mode="json", exclude_none=True
            )
            update = {"review_history": history, "approval": None, "error_type": None}
            if response.action == "modify":
                modification = response.modification
                if "requirements" in modification.model_fields_set:
                    update["requirement_input"] = [
                        r.model_dump(mode="json") for r in modification.requirements
                    ]
                if "evidences" in modification.model_fields_set:
                    update["evidence_input"] = [
                        e.model_dump(mode="json") for e in modification.evidences
                    ]
                if "configuration" in modification.model_fields_set:
                    update["configuration"] = dict(modification.configuration)
                update["status"] = "modified"
            else:
                update["status"] = "approved" if response.action == "approve" else "rejected"
                if response.action == "approve":
                    update["approval"] = response.model_dump(mode="json", exclude_none=True)
            return update
        except (ValidationError, ValueError, KeyError, TypeError) as exc:
            return {
                "status": "failed",
                "approval": None,
                "error_type": f"review_validation:{type(exc).__name__}",
            }

    def execute_approved_action(state):
        try:
            if state["status"] != "approved" or state.get("approval") is None:
                raise ValueError("approval required")
            snapshot = state["review_snapshot"]
            ReviewSnapshot.model_validate(snapshot)
            response = ReviewResponse.model_validate(state["approval"])
            check_response(snapshot, response)
            if (
                response.action != "approve"
                or snapshot["review_version"] != state["review_version"]
            ):
                raise ValueError("current approval required")
            if snapshot["run_id"] != state["run_id"] or snapshot["thread_id"] != state["thread_id"]:
                raise ValueError("approval belongs to a different run/thread")
            fresh = run_workflow(
                state["requirement_input"],
                evidences=state.get("evidence_input"),
                configuration=state.get("configuration"),
            ).model_dump(mode="json")
            if fresh != snapshot["business_result"] or fresh != state["business_result"]:
                raise ValueError("approved business object changed")
            if snapshot["configuration"] != state.get("configuration", {}):
                raise ValueError("approved configuration changed")
            payload = {
                "document_status": "DRAFT",
                "source_type": "mock",
                "human_review_status": "approved",
                "review_snapshot": deepcopy(snapshot),
                "review_response": response.model_dump(mode="json", exclude_none=True),
            }
            action = snapshot["proposed_action"]
            result = ledger.execute(
                action["operation_id"], payload, action["target_path"], after_publish=after_publish
            )
            return {"operation_result": result, "status": "completed", "error_type": None}
        except (ValidationError, ValueError, KeyError, TypeError, OSError) as exc:
            return {"status": "failed", "error_type": f"protected_execution:{type(exc).__name__}"}
        # Unexpected crashes deliberately propagate: graph/ledger recovery must handle them.

    def finalize_result(state):
        return {"status": state["status"]}

    graph = StateGraph(ReviewState)
    for name, node in (
        ("evaluate_requirements", evaluate_requirements),
        ("prepare_review", prepare_review),
        ("human_review", human_review),
        ("validate_review", validate_review),
        ("execute_approved_action", execute_approved_action),
        ("finalize_result", finalize_result),
    ):
        graph.add_node(name, node)
    graph.add_edge(START, "evaluate_requirements")
    graph.add_conditional_edges(
        "evaluate_requirements",
        lambda s: s["status"],
        {"failed": "finalize_result", "evaluated": "prepare_review"},
    )
    graph.add_edge("prepare_review", "human_review")
    graph.add_edge("human_review", "validate_review")
    graph.add_conditional_edges(
        "validate_review",
        lambda s: s["status"],
        {
            "approved": "execute_approved_action",
            "rejected": "finalize_result",
            "modified": "evaluate_requirements",
            "failed": "finalize_result",
        },
    )
    graph.add_edge("execute_approved_action", "finalize_result")
    graph.add_edge("finalize_result", END)
    compiled = graph.compile(checkpointer=checkpointer)

    def verify_completed(state):
        checked = execute_approved_action({**state, "status": "approved"})
        if checked["status"] != "completed":
            raise ValueError("completed artifact no longer matches the approved operation")
        return checked["operation_result"]

    # Keep the application integrity check attached to this compiled graph and its
    # ledger lifetime. SDK terminal snapshots alone cannot verify external files.
    compiled.verify_completed_operation = verify_completed
    return compiled


def thread_config(thread_id):
    if not isinstance(thread_id, str) or not thread_id.strip() or len(thread_id) > 128:
        raise ValueError("invalid thread ID")
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": 100}


def start_review(
    graph, thread_id, requirements, *, evidences=None, configuration=None, run_id=None
):
    config = thread_config(thread_id)
    if graph.get_state(config).values:
        raise ValueError("thread already exists; use status/resume")
    graph.invoke(
        {
            "requirement_input": deepcopy(requirements),
            "evidence_input": deepcopy(evidences),
            "configuration": deepcopy(configuration or {}),
            "run_id": run_id or uuid4().hex,
            "thread_id": thread_id,
            "review_version": 0,
            "review_history": {},
        },
        config,
    )
    return graph.get_state(config).values


def resume_review(graph, thread_id, payload):
    config = thread_config(thread_id)
    checkpoint = graph.get_state(config)
    state = checkpoint.values
    if not state:
        raise ValueError("unknown thread")
    response = ReviewResponse.model_validate(payload)
    check_response(state["review_snapshot"], response)
    prior = state["review_history"].get(str(response.review_version), {}).get("response")
    if prior is not None:
        if prior != response.model_dump(mode="json", exclude_none=True):
            raise ValueError("review already answered differently")
        if not checkpoint.next:
            if state["status"] == "completed":
                graph.verify_completed_operation(state)
            return state
        # Retry an interrupted execution task without submitting approval a second time.
        graph.invoke(None, config)
    else:
        if state["status"] != "awaiting_review":
            raise ValueError("thread is not awaiting review")
        graph.invoke(Command(resume=response.model_dump(mode="json", exclude_none=True)), config)
    return graph.get_state(config).values
