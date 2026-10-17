"""Single-process SOC application; existing graph owns business rules and review."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from time import perf_counter
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver

from agent_demo.agents.execution import wait_until
from agent_demo.domain.mock_cases import complete_evidence
from agent_demo.domain.reviews import ReviewResponse
from agent_demo.graphs.compliance_graph import run_workflow
from agent_demo.graphs.review_graph import (
    build_review_graph,
    check_response,
    resume_review,
    start_review,
    thread_config,
)
from agent_demo.integrations.rag_client import RAGClient, load_rag_settings
from agent_demo.integrations.rag_evidence import DocumentBinding, map_search_evidence
from agent_demo.observability import ObservedGraph, Trace
from agent_demo.persistence.operations import OperationLedger, _no_links
from agent_demo.soc.excel import export_soc
from agent_demo.soc.models import SOCInput


class TaskNotFound(ValueError):
    pass


def now():
    return datetime.now(UTC).isoformat()


class SOCService:
    def __init__(
        self, root, *, rag_factory=None, bindings=(), allowed_pdf_root=None, task_timeout=60
    ):
        if type(task_timeout) not in (int, float) or not 0 < task_timeout <= 300:
            raise ValueError("invalid task timeout")
        self.root = Path(root).absolute()
        self.runtime = self.root / "runtime" / "soc"
        _no_links(self.runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.database = self.runtime / "tasks.sqlite"
        self.lock = RLock()
        self.rag_factory = rag_factory
        self.bindings = [DocumentBinding.model_validate(b) for b in bindings]
        self.pdf_root = Path(allowed_pdf_root or self.root / "data" / "private")
        self.task_timeout = task_timeout
        with self.db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS soc_tasks (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, payload TEXT NOT NULL,
                status TEXT NOT NULL, error_type TEXT, audit TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            # A process restart never pretends an in-flight worker survived.
            db.execute(
                "UPDATE soc_tasks SET status='pending', error_type='restart_recovery' "
                "WHERE status='running'"
            )

    @contextmanager
    def db(self):
        _no_links(self.database)
        db = sqlite3.connect(self.database, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, task_id, owner):
        with self.db() as db:
            row = db.execute(
                "SELECT * FROM soc_tasks WHERE id=? AND owner=?", (task_id, owner)
            ).fetchone()
        if row is None:
            raise TaskNotFound("unknown task")
        item = dict(row)
        item["payload"], item["audit"] = json.loads(item["payload"]), json.loads(item["audit"])
        return item

    def update(self, task_id, status, error=None, audit=None):
        with self.db() as db:
            if audit is None:
                db.execute(
                    "UPDATE soc_tasks SET status=?,error_type=?,updated_at=? WHERE id=?",
                    (status, error, now(), task_id),
                )
            else:
                db.execute(
                    "UPDATE soc_tasks SET status=?,error_type=?,audit=?,updated_at=? WHERE id=?",
                    (status, error, json.dumps(audit), now(), task_id),
                )

    @contextmanager
    def graph(self, task_id=None):
        # The existing checkpoint and protected JSON ledger are isolated from demos.
        with (
            self.lock,
            OperationLedger(
                self.runtime / "review_operations.sqlite", self.root / "outputs" / "phase05"
            ) as ledger,
        ):
            with SqliteSaver.from_conn_string(str(self.runtime / "checkpoints.sqlite")) as saver:
                saver.setup()
                graph = build_review_graph(
                    saver,
                    ledger,
                    export_policy={"output_root": str((self.root / "outputs" / "soc").resolve())},
                )
                if task_id:
                    graph = ObservedGraph(
                        graph,
                        Trace(self.runtime / f"{task_id}.jsonl", run_id=task_id, thread_id=task_id),
                    )
                yield graph

    def submit(self, payload, owner):
        payload = SOCInput.model_validate(payload)
        if not owner or len(owner) > 128:
            raise ValueError("explicit authenticated owner required")
        values = payload.model_dump(mode="json")
        validation = run_workflow(
            values["requirements"],
            evidences=[],
            configuration=payload.configuration,
            evidence_mode=payload.source_type,
        )
        if validation.errors:
            raise ValueError("invalid requirement hierarchy")
        task_id = uuid4().hex
        with self.db() as db:
            db.execute(
                "INSERT INTO soc_tasks VALUES (?,?,?,?,?,?,?,?)",
                (task_id, owner, json.dumps(values), "pending", None, "{}", now(), now()),
            )
        return task_id

    def retrieve(self, payload, *, deadline):
        model = payload.requirements[0].model
        bindings = [b for b in self.bindings if b.model == model and b.applicability_confirmed]
        if len(bindings) != 1:
            raise ValueError("one trusted fixed-version document binding required")
        binding = bindings[0]
        if self.rag_factory is None:
            if os.getenv("AGENT_DEMO_LIVE_RAG_CONFIRM_READONLY") != "1":
                raise ValueError("safe read-only RAG not configured")

            def factory():
                return RAGClient(load_rag_settings())
        else:
            factory = self.rag_factory
        searches = []
        with factory() as client:
            attributes = dict.fromkeys(
                r.attribute for r in payload.requirements if r.kind == "atomic"
            )
            for attribute in attributes:
                if perf_counter() >= deadline:
                    raise TimeoutError("retrieval task deadline")
                searches.append(
                    client.retrieve(
                        f"{model} {attribute}",
                        document_id=binding.document_id,
                        version_id=binding.document_version,
                    )
                )
        if perf_counter() >= deadline:
            raise TimeoutError("retrieval task deadline; remote cancellation unconfirmed")
        evidences, proofs = map_search_evidence(searches, bindings, allowed_pdf_root=self.pdf_root)
        errors = {
            model: s.error or "retrieval_failed" for s in searches if s.retrieval_status == "failed"
        }
        return [e.model_dump(mode="json") for e in evidences], errors, proofs

    def run(self, task_id, owner):
        item = self.get(task_id, owner)
        if item["status"] != "pending":
            return self.status(task_id, owner)
        payload = SOCInput.model_validate(item["payload"])
        if not payload.input_confirmed:
            self.update(task_id, "pending", "input_confirmation_required")
            return self.status(task_id, owner)
        with self.db() as db:
            claimed = db.execute(
                "UPDATE soc_tasks SET status='running' WHERE id=? AND status='pending'", (task_id,)
            ).rowcount
        if not claimed:
            return self.status(task_id, owner)
        trace = Trace(self.runtime / f"{task_id}.jsonl", run_id=task_id, thread_id=task_id)
        trace.emit("USER_REQUEST", layer="soc", thread_id=task_id, status="running")
        try:
            with self.graph(task_id) as graph:
                state = graph.get_state(thread_config(task_id)).values
            if not state:
                deadline = perf_counter() + self.task_timeout
                errors = {}
                if payload.source_type == "mock":
                    evidences = (
                        [e.model_dump(mode="json") for e in payload.evidences]
                        if payload.evidences is not None
                        else complete_evidence(payload.requirements[0].model)
                    )
                else:
                    evidences, errors, _ = wait_until(
                        lambda: self.retrieve(payload, deadline=deadline), deadline
                    )
                if self.get(task_id, owner)["status"] == "cancelled":
                    return self.status(task_id, owner)
                if perf_counter() >= deadline:
                    raise TimeoutError("task deadline")
                with self.graph(task_id) as graph:
                    if self.get(task_id, owner)["status"] == "cancelled":
                        return self.status(task_id, owner)
                    state = start_review(
                        graph,
                        task_id,
                        [r.model_dump(mode="json") for r in payload.requirements],
                        evidences=evidences,
                        configuration=payload.configuration,
                        run_id=task_id,
                        evidence_mode=payload.source_type,
                        retrieval_errors=errors,
                    )
                    self.sync(task_id, state)
            else:
                with self.lock:
                    if self.get(task_id, owner)["status"] != "cancelled":
                        self.sync(task_id, state)
            trace.emit("HUMAN_REVIEW", layer="soc", thread_id=task_id, status=state["status"])
        except Exception as error:
            if self.get(task_id, owner)["status"] != "cancelled":
                self.update(task_id, "failed", type(error).__name__)
            trace.emit("ERROR", layer="soc", error_type=type(error).__name__, status="failed")
        return self.status(task_id, owner)

    def sync(self, task_id, state, audit=None):
        status = "cancelled" if state["status"] == "rejected" else state["status"]
        self.update(task_id, status, state.get("error_type"), audit)

    def status(self, task_id, owner):
        item = self.get(task_id, owner)
        with self.graph(task_id) as graph:
            state = graph.get_state(thread_config(task_id)).values
            graph_status = state.get("status")
            # Recover the application status after a process exited between a
            # durable graph checkpoint and updating the task row. Never revive
            # an explicitly cancelled task or invent a missing reviewer audit.
            if item["status"] != "cancelled" and graph_status in {
                "awaiting_review",
                "completed",
                "failed",
                "rejected",
            }:
                if graph_status == "completed":
                    if item["audit"].get("action") != "approve":
                        raise ValueError("approved checkpoint lacks durable reviewer audit")
                    graph.verify_completed_operation(state)
                expected = "cancelled" if graph_status == "rejected" else graph_status
                if item["status"] != expected:
                    self.sync(task_id, state)
                    item = self.get(task_id, owner)
        return {
            "task_id": task_id,
            "status": item["status"],
            "error_type": item["error_type"],
            "source_type": item["payload"]["source_type"],
            "audit": item["audit"],
            "review_snapshot": state.get("review_snapshot"),
            "business_result": state.get("business_result"),
            "created_at": item["created_at"],
            "updated_at": item["updated_at"],
        }

    def review(self, task_id, owner, payload):
        item = self.get(task_id, owner)
        if item["status"] not in {"awaiting_review", "completed", "cancelled"}:
            raise ValueError("task is not reviewable")
        if item["status"] == "cancelled" and item["audit"].get("action") != "reject":
            raise ValueError("cancelled task cannot be approved")
        response = ReviewResponse.model_validate(payload)
        if response.modification and response.modification.evidences is not None:
            raise ValueError("HTTP review cannot replace trusted source evidence")
        with self.graph(task_id) as graph:
            item = self.get(task_id, owner)
            if item["status"] == "cancelled" and item["audit"].get("action") != "reject":
                raise ValueError("cancelled task cannot be reviewed")
            before = graph.get_state(thread_config(task_id)).values
            check_response(before["review_snapshot"], response)
            updated = {
                **item["payload"],
                "requirements": before["requirement_input"],
                "configuration": before.get("configuration", {}),
            }
            if response.modification:
                if response.modification.requirements is not None:
                    updated["requirements"] = [
                        r.model_dump(mode="json") for r in response.modification.requirements
                    ]
                if response.modification.configuration is not None:
                    updated["configuration"] = response.modification.configuration
                SOCInput.model_validate(updated)
            if response.action == "modify" and item["payload"]["source_type"] == "real_rag":
                deadline = perf_counter() + self.task_timeout
                evidence, errors, _ = wait_until(
                    lambda: self.retrieve(SOCInput.model_validate(updated), deadline=deadline),
                    deadline,
                )
                if errors:
                    raise ValueError("modified evidence retrieval failed; approval unchanged")
                raw = response.model_dump(mode="json", exclude_none=True)
                raw["modification"]["evidences"] = evidence
            else:
                raw = response.model_dump(mode="json", exclude_none=True)
            prior = (
                before.get("review_history", {})
                .get(str(response.review_version), {})
                .get("response")
            )
            if prior is not None and prior != raw:
                raise ValueError("review already answered differently")
            audit = (
                item["audit"]
                if item["audit"].get("review_version") == response.review_version
                and item["audit"].get("action") == response.action
                else {
                    "reviewer": owner,
                    "reviewed_at": now(),
                    "action": response.action,
                    "review_version": response.review_version,
                }
            )
            # Persist reviewer/time before any protected action, so crash
            # recovery does not lose the identity bound to this approval.
            self.update(task_id, item["status"], item["error_type"], audit)
            state = resume_review(graph, task_id, raw)
            self.sync(task_id, state, audit)
            if response.action == "modify" and state["status"] == "awaiting_review":
                with self.db() as db:
                    db.execute(
                        "UPDATE soc_tasks SET payload=? WHERE id=?", (json.dumps(updated), task_id)
                    )
        Trace(self.runtime / f"{task_id}.jsonl", run_id=task_id, thread_id=task_id).emit(
            "HUMAN_REVIEW", layer="soc", thread_id=task_id, status=state["status"]
        )
        return self.status(task_id, owner)

    def cancel(self, task_id, owner):
        with self.lock:
            item = self.get(task_id, owner)
            if item["status"] == "completed":
                raise ValueError("completed effects cannot be cancelled or undone")
            self.update(task_id, "cancelled", "cancelled_no_rollback")
        return {"task_id": task_id, "status": "cancelled", "cancellation_confirmed": False}

    def export(self, task_id, owner, *, draft=False):
        with self.graph(task_id) as graph:
            item = self.get(task_id, owner)
            if item["status"] != "completed" and not (
                draft and item["status"] == "awaiting_review"
            ):
                raise ValueError(
                    "approval required; explicit draft export only while awaiting review"
                )
            state = graph.get_state(thread_config(task_id)).values
            if item["status"] == "completed":
                graph.verify_completed_operation(state)
            with OperationLedger(
                self.runtime / "excel_operations.sqlite",
                self.root / "outputs" / "soc",
                artifact_kind="soc_excel",
            ) as ledger:
                return export_soc(state, item["audit"], ledger)


def service_from_environment(root):
    """Only deployment-owned configuration selects document paths and RAG origin."""
    binding_file = os.getenv("AGENT_DEMO_SOC_BINDINGS")
    bindings = json.loads(Path(binding_file).read_text("utf-8-sig")) if binding_file else []
    return SOCService(root, bindings=bindings, allowed_pdf_root=os.getenv("AGENT_DEMO_PDF_ROOT"))
