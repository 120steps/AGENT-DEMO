"""Phase 6: offline control demo, or explicitly configured authorized HTTP retrieval."""

import argparse
import json
import os
from pathlib import Path

from agent_demo.agents.agentic_rag import run_agentic_rag
from agent_demo.config import load_model_settings
from agent_demo.evaluation.rag_benchmark import (
    OFFLINE_CASES,
    OfflineScriptedModel,
    compare_case,
    offline_benchmark,
    offline_client,
)
from agent_demo.integrations.rag_client import RAGClient, load_rag_settings
from agent_demo.integrations.rag_evidence import run_rag_workflow


def main():
    parser = argparse.ArgumentParser(description="Evidence-gated RAG; no old repo startup/login")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--scenario", choices=OFFLINE_CASES, default="single")
    parser.add_argument("--mode", choices=["retrieve", "agent", "benchmark"], default="agent")
    parser.add_argument("--query", default="Please retrieve the authorized product specifications.")
    parser.add_argument("--requirements", type=Path)
    parser.add_argument("--bindings", type=Path)
    parser.add_argument("--case-file", type=Path, help="Caller-verified live evaluation manifest")
    parser.add_argument("--document-id")
    parser.add_argument("--version-id")
    parser.add_argument("--classification")
    parser.add_argument("--chat", action="store_true", help="Caller-selected ordinary chat mode")
    args = parser.parse_args()
    try:
        if not args.offline and os.getenv("AGENT_DEMO_LIVE_RAG_CONFIRM_READONLY") != "1":
            raise ValueError("safe read-only service must be explicitly confirmed")
        scope = {
            k: v
            for k, v in {
                "document_id": args.document_id,
                "version_id": args.version_id,
                "classification": args.classification,
            }.items()
            if v
        }
        if args.mode == "benchmark":
            if not args.offline:
                if args.case_file is None:
                    raise ValueError("live benchmark requires an authorized real case set")
                from langchain_google_genai import ChatGoogleGenerativeAI

                settings = load_model_settings()
                manifest = json.loads(args.case_file.read_text("utf-8-sig"))
                if not manifest.get("live_cases"):
                    raise ValueError("real evaluation cases are missing")
                rows = []
                with RAGClient(load_rag_settings()) as client:
                    for case in manifest["live_cases"]:
                        model = ChatGoogleGenerativeAI(
                            model=settings.model,
                            api_key=settings.api_key,
                            temperature=0,
                            max_retries=0,
                        )
                        rows.append(
                            compare_case(
                                model,
                                client,
                                case["query"],
                                case_id=case["id"],
                                scope=case.get("scope", {}),
                                requirements=case.get("requirements"),
                                bindings=case.get("bindings", []),
                                allowed_pdf_root=Path(__file__).resolve().parents[1],
                                expected_status=case.get("expected_status"),
                                require_evidence=case.get("require_evidence", True),
                            )
                        )
                print(
                    json.dumps({"verification_mode": "live_http", "rows": rows}, ensure_ascii=True)
                )
                return 0
            print(json.dumps(offline_benchmark(), ensure_ascii=True))
            return 0
        client = offline_client(args.scenario) if args.offline else RAGClient(load_rag_settings())
        with client:
            if args.mode == "retrieve":
                search = client.retrieve(args.query, **scope)
                searches = [search]
                output = {
                    "retrieval_status": search.retrieval_status,
                    "error_type": search.error,
                    "result_count": len(search.results),
                    "elapsed_ms": search.elapsed_ms,
                }
            else:
                if args.offline:
                    model = OfflineScriptedModel(scenario=args.scenario)
                else:
                    from langchain_google_genai import ChatGoogleGenerativeAI

                    settings = load_model_settings()
                    model = ChatGoogleGenerativeAI(
                        model=settings.model, api_key=settings.api_key, temperature=0, max_retries=0
                    )
                result = run_agentic_rag(
                    model, client, args.query, scope=scope, require_evidence=not args.chat
                )
                searches = result.searches
                output = {
                    "agent_status": result.status,
                    "error_type": result.error_type,
                    "retrieval_calls": len(searches),
                    "model_rounds": result.model_rounds,
                    "citation_ids": list(result.citations),
                    "usage": result.usage,
                    "events": result.events,
                }
                if args.chat and result.answer:
                    output["candidate_llm_answer"] = result.answer.answer
            if args.requirements:
                requirements = json.loads(args.requirements.read_text("utf-8-sig"))
                bindings = json.loads(args.bindings.read_text("utf-8-sig")) if args.bindings else []
                outcome = run_rag_workflow(
                    requirements,
                    searches,
                    bindings=bindings,
                    allowed_pdf_root=Path(__file__).resolve().parents[1],
                    execution_error=(
                        "agent_" + output["agent_status"]
                        if output.get("agent_status") in {"failed", "timeout", "budget_exceeded"}
                        else None
                    ),
                )
                workflow = outcome["workflow"]
                output["business_status"] = workflow["overall_status"]
                output["decisions"] = workflow["decisions"]
                output["citation_verifications"] = outcome["citation_verifications"]
            output["verification_mode"] = "offline_mock" if args.offline else "live_http_unverified"
            print(json.dumps(output, ensure_ascii=True))
            return (
                1
                if output.get("agent_status") in {"failed", "timeout", "budget_exceeded"}
                or (output.get("retrieval_status") == "failed")
                else 0
            )
    except Exception as exc:
        reason = "configuration_or_input_error"
        if not args.offline and os.getenv("AGENT_DEMO_LIVE_RAG_CONFIRM_READONLY") != "1":
            reason = "safe_service_confirmation_required"
        elif not args.offline and not all(
            os.getenv(k) for k in ("AGENT_DEMO_RAG_BASE_URL", "AGENT_DEMO_RAG_TOKEN")
        ):
            reason = "rag_configuration_missing"
        print(
            json.dumps(
                {"status": "BLOCKED", "error_type": type(exc).__name__, "blocking_reason": reason}
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
