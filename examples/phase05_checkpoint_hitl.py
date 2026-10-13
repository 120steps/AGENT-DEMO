"""Persistent local MOCK review CLI. Each command opens and closes its connections."""

import argparse
import json
from contextlib import ExitStack
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from agent_demo.domain.mock_cases import scenarios
from agent_demo.graphs.review_graph import (
    build_review_graph,
    resume_review,
    start_review,
    thread_config,
)
from agent_demo.graphs.store_demo import run_store_demo
from agent_demo.persistence.operations import OperationLedger


def parser():
    result = argparse.ArgumentParser(description="Offline MOCK SOC human review")
    result.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    commands = result.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start")
    start.add_argument("--thread-id", required=True)
    start.add_argument("--scenario", choices=list(scenarios()), default="fully_satisfied")
    status = commands.add_parser("status")
    status.add_argument("--thread-id", required=True)
    resume = commands.add_parser("resume")
    resume.add_argument("--thread-id", required=True)
    resume.add_argument("--action", choices=["approve", "reject", "modify"], required=True)
    resume.add_argument("--review-id", required=True)
    resume.add_argument("--review-version", type=int, required=True)
    resume.add_argument("--snapshot-digest", required=True)
    resume.add_argument("--modification-json", type=Path)
    resume.add_argument("--comment", default="")
    commands.add_parser("store-demo")
    return result


def main():
    args = parser().parse_args()
    try:
        if args.command == "store-demo":
            print(json.dumps(run_store_demo(), ensure_ascii=True))
            return 0
        root = args.project_root.resolve()
        runtime = root / "runtime" / "phase05"
        runtime.mkdir(parents=True, exist_ok=True)
        with ExitStack() as stack:
            saver = stack.enter_context(
                SqliteSaver.from_conn_string(str(runtime / "checkpoints.sqlite"))
            )
            saver.setup()
            ledger = stack.enter_context(
                OperationLedger(runtime / "operations.sqlite", root / "outputs" / "phase05")
            )
            graph = build_review_graph(saver, ledger)
            if args.command == "start":
                requirements, evidence = scenarios()[args.scenario]
                state = start_review(graph, args.thread_id, requirements, evidences=evidence)
            elif args.command == "status":
                checkpoint = graph.get_state(thread_config(args.thread_id))
                if not checkpoint.values:
                    raise ValueError("unknown thread")
                state = dict(checkpoint.values)
                if state["status"] == "completed":
                    graph.verify_completed_operation(state)
                action = state.get("review_snapshot", {}).get("proposed_action")
                state["operation_record"] = ledger.get(action["operation_id"]) if action else None
                state["pending_nodes"] = list(checkpoint.next)
            else:
                payload = dict(
                    action=args.action,
                    review_id=args.review_id,
                    review_version=args.review_version,
                    snapshot_digest=args.snapshot_digest,
                    comment=args.comment,
                )
                if args.modification_json:
                    payload["modification"] = json.loads(
                        args.modification_json.read_text("utf-8-sig")
                    )
                state = resume_review(graph, args.thread_id, payload)
            print(json.dumps(state, ensure_ascii=True))
            return 1 if state["status"] == "failed" else 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
