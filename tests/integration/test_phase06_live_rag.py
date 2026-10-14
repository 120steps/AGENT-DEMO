"""Opt-in actual HTTP + actual caller-provided PDF acceptance; never start RAG-DEMO."""

import json
import os
import socket
from pathlib import Path

import pytest

from agent_demo.integrations.rag_client import RAGClient, RAGSettings, load_rag_settings
from agent_demo.integrations.rag_evidence import map_search_evidence


def test_real_network_failure_is_diagnostic_without_touching_old_service():
    # Bound, non-listening socket proves actual TCP failure, not a MockTransport.
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
        with RAGClient(
            RAGSettings(
                base_url=f"http://127.0.0.1:{port}",
                bearer_token="TEST-only",
                max_retries=0,
                connect_timeout=0.2,
                read_timeout=0.2,
                task_timeout=1,
            )
        ) as client:
            result = client.retrieve("test unavailable service")
        assert result.retrieval_status == "failed"
        assert result.error in {"network_error", "timeout", "budget_exceeded"}


def test_live_http_and_pdf_evidence_requires_explicit_safe_service_configuration():
    if os.getenv("AGENT_DEMO_LIVE_RAG_CONFIRM_READONLY") != "1":
        pytest.skip("BLOCKED: safe read-only live service/PDF not configured; no old repo startup")
    root = Path(__file__).resolve().parents[2]
    binding_path = Path(os.environ["AGENT_DEMO_RAG_BINDINGS_JSON"]).resolve()
    assert binding_path.is_relative_to(root)
    bindings = json.loads(binding_path.read_text("utf-8-sig"))
    query = os.environ["AGENT_DEMO_RAG_TEST_QUERY"]
    with RAGClient(load_rag_settings()) as client:
        search = client.retrieve(
            query,
            document_id=bindings[0]["document_id"],
            version_id=bindings[0]["document_version"],
        )
        assert search.retrieval_status == "ok" and search.results
        evidences, proofs = map_search_evidence([search], bindings, allowed_pdf_root=root)
        assert evidences and any(p["verified"] for p in proofs)
        assert all(e.source_text in {h.original_text for h in search.results} for e in evidences)
