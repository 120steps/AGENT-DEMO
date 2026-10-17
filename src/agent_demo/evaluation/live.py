"""Opt-in existing real integrations. No startup, key search, indexing or downloads."""

import json
import os
from pathlib import Path
from time import perf_counter

from agent_demo.agents.tool_calling import run_tool_calling
from agent_demo.config import load_model_settings
from agent_demo.evaluation.models import Observation
from agent_demo.integrations.gemini import GeminiClient
from agent_demo.integrations.rag_client import RAGClient, load_rag_settings
from agent_demo.integrations.rag_evidence import map_search_evidence


def live_case(case, trace, temporary):
    if case.execution_mode == "real_llm":
        client = GeminiClient(load_model_settings())
        usage, versions, latency = [], [], []

        class ProviderObserver:
            def _invoke(self, method, *args):
                started = perf_counter()
                reply = method(*args)
                latency.append((perf_counter() - started) * 1000)
                if reply.usage:
                    usage.append(reply.usage)
                    trace.emit("MODEL_USAGE", layer="provider", token_usage=reply.usage)
                if reply.model_version:
                    versions.append(reply.model_version)
                return reply

            def first(self, *args):
                return self._invoke(client.first, *args)

            def finish(self, *args):
                return self._invoke(client.finish, *args)

        try:
            result = run_tool_calling(
                ProviderObserver(), "What is 15 + 27?", event_sink=trace.import_event
            )
        finally:
            client.close()
        executions = [e for e in result.events if e["event"] == "TOOL_EXECUTION"]
        returned = [
            e["result"]["result"]
            for e in result.events
            if e["event"] == "TOOL_RESULT" and e["result"].get("status") == "ok"
        ]
        return Observation(
            result.status,
            facts={
                "executed": len(executions),
                "tool_results": returned,
                "provider": "gemini",
                "model_id": client.model,
                "response_versions": versions,
            },
            tools=[
                {
                    "name": e["tool_name"],
                    "executed": True,
                    "success": e["execution_status"] == "completed",
                }
                for e in executions
            ],
            actions=[e["tool_name"] for e in executions],
            model_calls=len(latency),
            model_latency_ms=sum(latency),
            tool_latency_ms=sum(e.get("elapsed_ms", 0) for e in executions),
            token_usage={
                k: sum(u.get(k, 0) for u in usage)
                for k in ("input_tokens", "output_tokens", "total_tokens")
            }
            if usage
            else None,
        )
    project = Path(__file__).resolve().parents[3]
    path = Path(os.environ["AGENT_DEMO_RAG_BINDINGS_JSON"]).resolve()
    if not path.is_relative_to(project):
        raise ValueError("binding path must be inside caller project")
    bindings = json.loads(path.read_text("utf-8-sig"))
    with RAGClient(load_rag_settings()) as client:
        result = client.retrieve(os.environ["AGENT_DEMO_RAG_TEST_QUERY"])
    evidences, proofs = map_search_evidence([result], bindings, allowed_pdf_root=project)
    verified = any(p["verified"] for p in proofs)
    trace.emit("CITATION_CHECK", layer="evidence", status="verified" if verified else "rejected")
    return Observation(
        "verified_citation" if verified else "PENDING",
        evidence={"pdf_verified": verified, "ids": [e.id for e in evidences]},
        citations=[
            {
                "accepted": p["verified"],
                "membership_valid": True,
                "pdf_checked": True,
                "pdf_verified": p["verified"],
                "source_consistent": p["verified"],
            }
            for p in proofs
        ],
        tools=[
            {
                "name": "search_knowledge_base",
                "executed": True,
                "success": result.retrieval_status != "failed",
            }
        ],
        retrieval_calls=1,
        tool_latency_ms=result.elapsed_ms,
    )
