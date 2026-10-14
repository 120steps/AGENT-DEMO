"""Offline HTTP contract tests; MockTransport is not a real RAG verification."""

import json
import time

import httpx
import pytest
from pydantic import ValidationError

from agent_demo.integrations.rag_client import RAGClient, RAGSettings, load_rag_settings


def settings(**updates):
    return RAGSettings(
        **{
            "base_url": "http://127.0.0.1:8011",
            "bearer_token": "offline-test-token",
            "knowledge_base_id": "authorized-mock-kb",
            **updates,
        }
    )


def document(**updates):
    return {
        "document": "MOCK-SW-48 has 48 GE downlink ports. MOCK fixture only.",
        "source": "MOCK-datasheet.pdf",
        "page": 2,
        "chunk_id": 0,
        "document_id": "mock-doc-id",
        "version_id": "mock-version-id",
        "chunk_uid": "actual-server-chunk-uid",
        "vector_distance": 0.15,
        "fusion_score": 1.5,
        "rerank_score": None,
        "metadata": {"content_hash": "a" * 64, "provided_model": "MOCK-SW-48"},
        **updates,
    }


def client(handler, **updates):
    return RAGClient(settings(**updates), transport=httpx.MockTransport(handler))


def test_real_v3_request_fields_and_preserved_independent_evidence_fields():
    seen = []
    item = document()

    def handler(request):
        seen.append(request)
        assert request.url == "http://127.0.0.1:8011/retrieve"
        assert request.method == "POST"
        assert request.headers["authorization"] == "Bearer offline-test-token"
        assert json.loads(request.content) == {
            "question": "MOCK port requirement",
            "knowledge_base_id": "authorized-mock-kb",
            "top_k": 3,
            "document_id": "mock-doc-id",
            "version_id": "mock-version-id",
            "classification": "public",
        }
        return httpx.Response(200, json={"documents": [item], "latency_ms": 12})

    with client(handler, page_number_semantics="pdf_physical_1_based") as rag:
        result = rag.retrieve(
            "MOCK port requirement",
            top_k=3,
            document_id="mock-doc-id",
            version_id="mock-version-id",
            classification="public",
        )
    assert result.retrieval_status == "ok"
    hit = result.results[0]
    assert hit.original_text == item["document"]
    assert hit.page == 2 and hit.chunk_id == 0
    assert hit.page_number_semantics == "pdf_physical_1_based"
    assert hit.document_version == item["version_id"]
    assert hit.document_hash == "a" * 64
    assert hit.raw_document == item and hit.metadata == item["metadata"]
    assert hit.scores == {"vector_distance": 0.15, "fusion_score": 1.5, "rerank_score": None}
    assert "score" not in hit.model_dump()
    assert result.retrieval_metadata["attempt_count"] == 1
    assert result.retrieval_metadata["server_metadata"]["latency_ms"] == 12
    assert len(seen) == 1


def test_missing_fields_remain_unknown_and_page_not_changed():
    with client(
        lambda request: httpx.Response(200, json={"documents": [{"document": "raw"}]})
    ) as rag:
        hit = rag.retrieve("query").results[0]
    assert hit.page is None and hit.chunk_id is None
    assert hit.source is None and hit.document_id is None
    assert hit.document_version is None and hit.document_hash is None
    assert hit.metadata is None and hit.page_number_semantics == "unknown"
    with client(lambda request: httpx.Response(200, json={"documents": [document(page=0)]})) as rag:
        hit = rag.retrieve("query").results[0]
    assert hit.page == 0 and hit.page_number_semantics == "unknown"


def test_actual_metadata_fallback_does_not_invent_provenance_or_hash():
    raw = {"document": "raw", "metadata": {"page": 7, "chunk_id": 1, "version_id": "provided"}}
    with client(lambda request: httpx.Response(200, json={"documents": [raw]})) as rag:
        hit = rag.retrieve("query").results[0]
    assert hit.page == 7 and hit.document_version == "provided"
    assert hit.document_hash is None and hit.source is None
    assert hit.raw_document == raw


def test_empty_authorization_branch_and_absent_normal_latency():
    body = {
        "documents": [],
        "refused": True,
        "refusal_reason": "no_authorized_documents",
        "retrieval_latency_ms": 0,
    }
    with client(lambda request: httpx.Response(200, json=body)) as rag:
        result = rag.retrieve("query")
    assert result.retrieval_status == "empty" and result.results == []
    assert result.error is None
    assert result.retrieval_metadata["server_metadata"]["refused"] is True


@pytest.mark.parametrize(
    "url",
    [
        "http://remote.example",
        "file:///private",
        "ftp://localhost",
        "http://localhost.evil.invalid",
        "http://127.0.0.1:8011/retrieve",
        "https://example.com/api",
        "https://user:secret@example.com",
        "https://example.com?token=secret",
        "https://example.com#fragment",
        "https://example.com?",
        "https://example.com#",
        "https://example.com:0",
        "http://localhost:65536",
        " http://localhost",
        "http://localhost\n",
        "https://example.com\\unexpected",
    ],
)
def test_untrusted_or_unexpected_origin_is_rejected_without_network(url):
    with pytest.raises(ValidationError):
        settings(base_url=url)


@pytest.mark.parametrize(
    "url", ["http://localhost:8011/", "http://[::1]:8011", "https://rag.example"]
)
def test_explicit_supported_origin(url):
    assert settings(base_url=url).base_url == url.rstrip("/")


def test_credentials_excluded_from_repr_dump_and_config_error():
    configured = settings()
    assert "offline-test-token" not in repr(configured)
    assert "offline-test-token" not in configured.model_dump_json()
    with pytest.raises(ValidationError) as error:
        settings(bearer_token="secret\nvalue")
    assert "secret" not in str(error.value)
    loaded = load_rag_settings(
        {
            "AGENT_DEMO_RAG_BASE_URL": "http://localhost:8011",
            "AGENT_DEMO_RAG_TOKEN": "explicit-secret",
            "AGENT_DEMO_RAG_KB": "kb-test",
        }
    )
    assert loaded.knowledge_base_id == "kb-test"
    with pytest.raises(ValidationError):
        load_rag_settings({})


@pytest.mark.parametrize(
    "query,options",
    [
        ("", {}),
        ("   ", {}),
        ("x" * 4001, {}),
        (True, {}),
        ("query", {"top_k": True}),
        ("query", {"top_k": "3"}),
        ("query", {"top_k": 0}),
        ("query", {"top_k": 11}),
        ("query", {"document_id": {"path": "secret"}}),
    ],
)
def test_invalid_arguments_are_rejected_before_request(query, options):
    calls = []
    with client(lambda request: calls.append(request)) as rag:
        result = rag.retrieve(query, **options)
    assert result.retrieval_status == "failed" and result.error == "invalid_request"
    assert result.retrieval_metadata["attempt_count"] == 0
    assert calls == []


@pytest.mark.parametrize(
    "status,error", [(401, "auth_failed"), (403, "auth_failed"), (404, "http_error")]
)
def test_http_errors_do_not_leak_response_body_or_retry_authentication(status, error):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="private-error-body offline-test-token")

    with client(handler) as rag:
        result = rag.retrieve("query")
    assert result.error == error
    assert "private-error-body" not in result.model_dump_json()
    assert "offline-test-token" not in result.model_dump_json()
    assert len(calls) == 1


def test_redirect_cannot_forward_credentials_to_another_origin():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(307, headers={"Location": "https://unapproved.example/steal"})

    with client(handler) as rag:
        result = rag.retrieve("query")
    assert result.error == "redirect_not_allowed"
    assert calls == ["http://127.0.0.1:8011/retrieve"]


@pytest.mark.parametrize("status", [429, 500, 503])
def test_retryable_status_has_finite_attempts_and_records_success(status):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(status)
        return httpx.Response(200, json={"documents": [document()]})

    with client(handler, max_retries=1) as rag:
        result = rag.retrieve("query")
    assert result.retrieval_status == "ok"
    assert result.retrieval_metadata["attempt_count"] == 2
    calls.clear()
    with client(
        lambda request: calls.append(request) or httpx.Response(status), max_retries=2
    ) as rag:
        result = rag.retrieve("query")
    assert result.error == "http_error" and len(calls) == 3


def test_retry_after_cannot_extend_task_budget():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "120"})

    with client(handler, task_timeout=0.1, max_retries=3) as rag:
        result = rag.retrieve("query")
    assert result.error == "budget_exceeded"
    assert len(calls) == 1


@pytest.mark.parametrize("field", ["connect_timeout", "read_timeout", "task_timeout"])
def test_timeout_configuration_rejects_boolean_or_nonfinite_values(field):
    for value in (True, float("nan"), float("inf"), "10"):
        with pytest.raises(ValidationError):
            settings(**{field: value})


@pytest.mark.parametrize(
    "exception,error",
    [
        (httpx.ReadTimeout, "timeout"),
        (httpx.ConnectError, "network_error"),
    ],
)
def test_network_exceptions_are_diagnostic_and_bounded(exception, error):
    calls = []

    def handler(request):
        calls.append(request)
        raise exception("private-message offline-test-token", request=request)

    with client(handler, max_retries=1) as rag:
        result = rag.retrieve("query")
    assert result.error == error and len(calls) == 2
    assert "private-message" not in result.model_dump_json()


@pytest.mark.parametrize(
    "body",
    [
        {"documents": "bad"},
        {"documents": [None]},
        {"unexpected": "shape"},
        {"documents": [document(page=True)]},
        {"documents": [document(chunk_id="0")]},
        {"documents": [document(vector_distance=float("inf"))]},
        {"documents": [document(metadata="bad")]},
        {"documents": [document(document=48)]},
    ],
)
def test_bad_response_is_schema_failure(body):
    with client(lambda request: httpx.Response(200, json=body)) as rag:
        result = rag.retrieve("query")
    assert result.error == "schema_error" and result.results == []


def test_non_json_response_and_contradictory_page_semantics_are_rejected():
    with client(lambda request: httpx.Response(200, content=b"not JSON")) as rag:
        assert rag.retrieve("query").error == "schema_error"
    with client(
        lambda request: httpx.Response(200, json={"documents": [document(page=0)]}),
        page_number_semantics="pdf_physical_1_based",
    ) as rag:
        assert rag.retrieve("query").error == "schema_error"


def test_bounded_result_count_and_response_body_size():
    with client(lambda request: httpx.Response(200, json={"documents": [document()] * 4})) as rag:
        result = rag.retrieve("query", top_k=2)
    assert len(result.results) == 2
    assert result.retrieval_metadata["truncated_results"] == 2
    with client(
        lambda request: httpx.Response(200, content=b"x" * 100), max_response_bytes=50
    ) as rag:
        assert rag.retrieve("query").error == "response_too_large"


def test_logical_deadline_rejects_slow_response_without_claiming_cancellation():
    calls = []

    def handler(request):
        calls.append(request)
        assert 0 < request.extensions["timeout"]["read"] <= 0.002
        time.sleep(0.01)
        return httpx.Response(200, json={"documents": [document()]})

    with client(handler, task_timeout=0.002, max_retries=3) as rag:
        result = rag.retrieve("query")
    assert result.error == "budget_exceeded" and result.results == []
    assert result.elapsed_ms >= 10
    assert len(calls) == 1


def test_streamed_body_limit_closes_response_and_closed_client_is_not_reused():
    class Stream(httpx.SyncByteStream):
        closed = False

        def __iter__(self):
            yield b"x" * 25
            yield b"x" * 26
            raise AssertionError("must stop reading when body limit is exceeded")

        def close(self):
            self.closed = True

    stream = Stream()
    with client(lambda request: httpx.Response(200, stream=stream), max_response_bytes=50) as rag:
        assert rag.retrieve("query").error == "response_too_large"
    assert stream.closed is True
    assert rag.retrieve("query").error == "client_closed"
