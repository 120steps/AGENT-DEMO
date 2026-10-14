"""Explicit OFFLINE script fixtures and a live-capable fixed/agentic comparison.

Scripted model outputs are predetermined test data, never a real LLM decision.
"""

import json
from time import perf_counter

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr

from agent_demo.agents.agentic_rag import run_agentic_rag
from agent_demo.integrations.rag_client import RAGClient, RAGSettings
from agent_demo.integrations.rag_evidence import run_rag_workflow

OFFLINE_CASES = ("greeting", "single", "supplement", "empty", "conflict", "service_error")


class OfflineScriptedModel(BaseChatModel):
    scenario: str
    _round: int = PrivateAttr(default=0)

    @property
    def _llm_type(self):
        return "phase06-offline-script-not-llm"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self._round += 1
        if self.scenario == "greeting":
            response = AIMessage(content="Hello (OFFLINE SCRIPT, no model API).")
        elif self._round == 1 or (self.scenario == "supplement" and self._round == 2):
            response = AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": f"offline-search-{self._round}",
                        "name": "search_knowledge_base",
                        "args": {
                            "query": "OFFLINE TEST product specification"
                            if self._round == 1
                            else "OFFLINE TEST supplementary downlink specification"
                        },
                    }
                ],
            )
        else:
            ids = []
            for message in messages:
                if isinstance(message, ToolMessage) and message.name == "search_knowledge_base":
                    payload = json.loads(message.content)
                    ids.extend(s["citation_id"] for s in payload.get("snippets", []))
            response = AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "offline-final",
                        "name": "RAGAgentAnswer",
                        "args": {
                            "answer": "OFFLINE scripted candidate; "
                            "not a verified compliance decision.",
                            "citation_ids": list(dict.fromkeys(ids)),
                            "needs_more_evidence": not bool(ids),
                        },
                    }
                ],
            )
        return ChatResult(generations=[ChatGeneration(message=response)])


def offline_client(scenario):
    if scenario not in OFFLINE_CASES:
        raise ValueError("unknown offline scenario")
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        if scenario == "service_error":
            return httpx.Response(503, json={"error": "OFFLINE simulated failure"})
        documents = []
        if scenario not in {"empty", "greeting"} and not (
            scenario == "supplement" and attempts == 1
        ):
            documents = [
                {
                    "document": "TEST ONLY\nDownlink ports: 48 count",
                    "source": "TEST-only-spec.pdf",
                    "page": 1,
                    "chunk_id": 0,
                    "document_id": "test-doc",
                    "version_id": "test-version",
                    "metadata": {"fixture_type": "offline_mock"},
                }
            ]
            if scenario == "conflict":
                documents.append(
                    {
                        **documents[0],
                        "document": "TEST ONLY\nDownlink ports: 24 count",
                        "source": "TEST-only-conflict.pdf",
                        "chunk_id": 1,
                    }
                )
        return httpx.Response(200, json={"documents": documents})

    return RAGClient(
        RAGSettings(
            base_url="https://offline.invalid", bearer_token="OFFLINE-NO-SECRET", max_retries=0
        ),
        transport=httpx.MockTransport(handler),
    )


def compare_case(
    model,
    client,
    query,
    *,
    case_id,
    require_evidence=True,
    scope=None,
    requirements=None,
    bindings=(),
    allowed_pdf_root=None,
    expected_status=None,
):
    started = perf_counter()
    baseline = client.retrieve(query, **(scope or {}))
    baseline_ms = (perf_counter() - started) * 1000
    agent = run_agentic_rag(model, client, query, scope=scope, require_evidence=require_evidence)
    row = {
        "case_id": case_id,
        "baseline": {
            "retrieval_status": baseline.retrieval_status,
            "retrieval_calls": 1,
            "elapsed_ms": round(baseline_ms, 3),
            "result_count": len(baseline.results),
            "error_type": baseline.error,
            "token_usage": None,
        },
        "agentic": {
            "status": agent.status,
            "retrieval_calls": len(agent.searches),
            "elapsed_ms": agent.elapsed_ms,
            "citation_count": len(agent.citations),
            "citation_membership_valid": agent.answer is None
            or all(cid in agent.citations for cid in agent.answer.citation_ids),
            "token_usage": agent.usage,
            "error_type": agent.error_type,
        },
    }
    if requirements is not None:
        for name, searches in (("baseline", [baseline]), ("agentic", agent.searches)):
            outcome = run_rag_workflow(
                requirements,
                searches,
                bindings=bindings,
                allowed_pdf_root=allowed_pdf_root,
                execution_error=(
                    "agent_" + agent.status
                    if name == "agentic"
                    and agent.status in {"failed", "timeout", "budget_exceeded"}
                    else None
                ),
            )
            workflow = outcome["workflow"]
            row[name]["business_status"] = workflow["overall_status"]
            row[name]["task_success"] = (
                workflow["overall_status"] == expected_status if expected_status else None
            )
            proofs = {p["citation_id"]: p["verified"] for p in outcome["citation_verifications"]}
            chosen = (
                list(proofs)
                if name == "baseline"
                else (agent.answer.citation_ids if agent.answer else [])
            )
            row[name]["pdf_citation_accuracy"] = (
                sum(proofs.get(cid, False) for cid in chosen) / len(chosen) if chosen else None
            )
            row[name]["http_attempts"] = sum(
                s.retrieval_metadata.get("attempt_count", 0) for s in searches
            )
    return row


def offline_benchmark():
    rows = []
    for scenario in OFFLINE_CASES:
        # Separate response scripts reset the same fixture for a fair API input.
        with offline_client(scenario) as baseline_client:
            baseline = baseline_client.retrieve("OFFLINE TEST question")
        with offline_client(scenario) as agent_client:
            result = run_agentic_rag(
                OfflineScriptedModel(scenario=scenario),
                agent_client,
                "OFFLINE TEST question",
                require_evidence=scenario != "greeting",
            )
        rows.append(
            {
                "case_id": scenario,
                "baseline_status": baseline.retrieval_status,
                "baseline_calls": 1,
                "agent_status": result.status,
                "agent_calls": len(result.searches),
                "elapsed_ms": result.elapsed_ms,
                "token_usage": result.usage,
            }
        )
    return {
        "verification_mode": "offline_mock",
        "rows": rows,
        "real_document_success_rate": None,
        "real_pdf_citation_accuracy": None,
        "real_benchmark_status": "BLOCKED",
        "conclusion": "Script fixtures validate control flow; "
        "they cannot establish real Agentic RAG superiority.",
    }
