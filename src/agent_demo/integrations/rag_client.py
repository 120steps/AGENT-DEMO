"""Bounded V3 /retrieve client. Retrieved text is data, never permission or code."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping
from copy import deepcopy
from typing import Literal
from urllib.parse import urlsplit

import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    ValidationError,
    field_validator,
)

PageSemantics = Literal["unknown", "pdf_physical_1_based"]


class RAGSettings(BaseModel):
    """Trusted process configuration; a model/tool cannot select an endpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    base_url: StrictStr
    bearer_token: StrictStr = Field(repr=False, exclude=True)
    knowledge_base_id: StrictStr = Field(default="default", min_length=1, max_length=200)
    connect_timeout: float = Field(default=3, gt=0, le=120, allow_inf_nan=False)
    read_timeout: float = Field(default=10, gt=0, le=120, allow_inf_nan=False)
    task_timeout: float = Field(default=20, gt=0, le=300, allow_inf_nan=False)
    max_retries: StrictInt = Field(default=1, ge=0, le=3)
    max_results: StrictInt = Field(default=10, ge=1, le=50)
    max_response_bytes: StrictInt = Field(default=2 * 1024 * 1024, ge=1, le=8 * 1024 * 1024)
    page_number_semantics: PageSemantics = "unknown"

    @field_validator("base_url")
    @classmethod
    def fixed_origin(cls, value):
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError as exc:
            raise ValueError("invalid configured RAG origin") from exc
        if (
            not value
            or any(char.isspace() or ord(char) < 32 for char in value)
            or parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
            or "?" in value
            or "#" in value
            or "\\" in value
            or (port is not None and port <= 0)
            or (
                parsed.scheme == "http"
                and parsed.hostname.lower() not in {"localhost", "127.0.0.1", "::1"}
            )
        ):
            raise ValueError("RAG URL must be an HTTPS origin or HTTP loopback origin")
        return value.rstrip("/")

    @field_validator("bearer_token", "knowledge_base_id")
    @classmethod
    def nonempty_configuration(cls, value):
        if not value.strip() or any(ord(char) < 32 for char in value):
            raise ValueError("empty or invalid RAG configuration")
        if any(char.isspace() for char in value):
            raise ValueError("RAG token and knowledge base ID cannot contain whitespace")
        return value

    @field_validator("connect_timeout", "read_timeout", "task_timeout", mode="before")
    @classmethod
    def numeric_timeout(cls, value):
        if type(value) not in {float, int}:
            raise ValueError("timeout must be a finite positive number")
        return value


def load_rag_settings(environ: Mapping[str, str] | None = None) -> RAGSettings:
    """Read explicit process settings, never load the old repository's secrets."""
    values = os.environ if environ is None else environ
    return RAGSettings(
        base_url=values.get("AGENT_DEMO_RAG_BASE_URL", ""),
        bearer_token=values.get("AGENT_DEMO_RAG_TOKEN", ""),
        knowledge_base_id=values.get("AGENT_DEMO_RAG_KB", "default"),
        page_number_semantics=values.get("AGENT_DEMO_RAG_PAGE_SEMANTICS", "unknown"),
    )


class RAGHit(BaseModel):
    """Actual retrieval fields, with missing information represented by None."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    original_text: StrictStr | None = None
    source: StrictStr | None = None
    page: StrictInt | None = Field(default=None, ge=0)
    chunk_id: StrictInt | None = Field(default=None, ge=0)
    document_id: StrictStr | None = None
    document_version: StrictStr | None = None
    chunk_uid: StrictStr | None = None
    document_hash: StrictStr | None = None
    page_number_semantics: PageSemantics = "unknown"
    metadata: dict | None = None
    scores: dict[str, float | None] = Field(default_factory=dict)
    raw_document: dict = Field(default_factory=dict)

    @field_validator("scores", mode="before")
    @classmethod
    def finite_scores(cls, scores):
        for value in scores.values():
            if value is not None and (
                type(value) not in {int, float} or not (-float("inf") < value < float("inf"))
            ):
                raise ValueError("score must be a finite number or unknown")
        return scores


class RAGSearchResult(BaseModel):
    query: str
    results: list[RAGHit] = Field(default_factory=list)
    retrieval_status: Literal["ok", "empty", "failed"]
    error: str | None = None
    elapsed_ms: float
    retrieval_metadata: dict = Field(default_factory=dict)


class RetrieveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    question: StrictStr = Field(min_length=1, max_length=4000)
    knowledge_base_id: StrictStr
    top_k: StrictInt = Field(ge=1, le=50)
    document_id: StrictStr | None = Field(default=None, min_length=1, max_length=200)
    version_id: StrictStr | None = Field(default=None, min_length=1, max_length=200)
    classification: StrictStr | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("question")
    @classmethod
    def nonempty_question(cls, value):
        if not value.strip():
            raise ValueError("question must contain text")
        return value


def _reject_non_json_number(_value):
    raise ValueError("nonfinite JSON number")


class RAGClient:
    """Own and close a synchronous HTTPX client with bounded logical deadlines.

    HTTPX timeouts bound individual connect/read/write waits, not the entire
    task. We check a monotonic deadline before/after calls and each body chunk.
    An in-flight synchronous wait may finish after that logical deadline; this
    does not claim cancellation of the remote retrieval or its side effects.
    """

    def __init__(self, settings: RAGSettings, *, transport=None):
        self.settings = settings
        self.verification_mode = "offline_mock" if transport is not None else "live_http"
        self._client = httpx.Client(
            follow_redirects=False,
            trust_env=False,
            transport=transport,
            headers={
                "Authorization": f"Bearer {settings.bearer_token}",
                "Accept": "application/json",
                "Accept-Encoding": "identity",
            },
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        self._client.close()

    def _hits(self, data, limit):
        documents = data.get("documents")
        if type(documents) is not list:
            raise ValueError("missing documents array")
        hits = []
        for item in documents[:limit]:
            if type(item) is not dict:
                raise ValueError("retrieval document must be an object")
            metadata = item.get("metadata")
            if metadata is not None and type(metadata) is not dict:
                raise ValueError("metadata must be an object or unknown")
            fallback = metadata or {}
            page = item.get("page", fallback.get("page"))
            semantics = self.settings.page_number_semantics if page is not None else "unknown"
            if semantics == "pdf_physical_1_based" and (type(page) is not int or page < 1):
                raise ValueError("page contradicts configured 1-based physical semantics")
            hits.append(
                RAGHit(
                    original_text=item.get("document"),
                    source=item.get("source", fallback.get("source")),
                    page=page,
                    chunk_id=item.get("chunk_id", fallback.get("chunk_id")),
                    document_id=item.get("document_id", fallback.get("document_id")),
                    document_version=item.get("version_id", fallback.get("version_id")),
                    chunk_uid=item.get("chunk_uid", fallback.get("chunk_uid")),
                    document_hash=fallback.get("content_hash", fallback.get("document_hash")),
                    page_number_semantics=semantics,
                    metadata=deepcopy(metadata),
                    scores={
                        key: item[key]
                        for key in ("vector_distance", "fusion_score", "rerank_score")
                        if key in item
                    },
                    raw_document=deepcopy(item),
                )
            )
        return hits, max(0, len(documents) - limit)

    def retrieve(
        self, query, top_k=None, document_id=None, version_id=None, classification=None
    ) -> RAGSearchResult:
        start = time.monotonic()
        deadline = start + self.settings.task_timeout
        attempts = 0
        metadata = {"verification_mode": self.verification_mode}

        def outcome(status="failed", error=None, results=None):
            return RAGSearchResult(
                query=query if isinstance(query, str) else "",
                results=results or [],
                retrieval_status=status,
                error=error,
                elapsed_ms=round((time.monotonic() - start) * 1000, 3),
                retrieval_metadata={**metadata, "attempt_count": attempts},
            )

        if self._client.is_closed:
            return outcome(error="client_closed")
        try:
            request = RetrieveRequest(
                question=query,
                knowledge_base_id=self.settings.knowledge_base_id,
                top_k=self.settings.max_results if top_k is None else top_k,
                document_id=document_id,
                version_id=version_id,
                classification=classification,
            )
            if request.top_k > self.settings.max_results:
                return outcome(error="invalid_request")
        except ValidationError:
            return outcome(error="invalid_request")

        last_error = "network_error"
        for _ in range(self.settings.max_retries + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return outcome(error="budget_exceeded")
            attempts += 1
            timeout = httpx.Timeout(
                min(self.settings.read_timeout, remaining),
                connect=min(self.settings.connect_timeout, remaining),
                write=min(self.settings.read_timeout, remaining),
                pool=min(self.settings.connect_timeout, remaining),
            )
            try:
                with self._client.stream(
                    "POST",
                    f"{self.settings.base_url}/retrieve",
                    json=request.model_dump(exclude_none=True),
                    timeout=timeout,
                ) as response:
                    metadata["http_status"] = response.status_code
                    if time.monotonic() >= deadline:
                        return outcome(error="budget_exceeded")
                    if response.status_code in {401, 403}:
                        return outcome(error="auth_failed")
                    if 300 <= response.status_code < 400:
                        return outcome(error="redirect_not_allowed")
                    if response.status_code in {429, 500, 503}:
                        last_error = "http_error"
                        if attempts <= self.settings.max_retries:
                            # Respect numeric Retry-After without extending the
                            # task deadline. HTTP-date form is not interpreted.
                            try:
                                delay = float(response.headers.get("Retry-After", "0"))
                            except ValueError:
                                delay = 0
                            if 0 < delay < float("inf"):
                                if delay >= deadline - time.monotonic():
                                    return outcome(error="budget_exceeded")
                                time.sleep(delay)
                        continue
                    if not 200 <= response.status_code < 300:
                        return outcome(error="http_error")
                    declared = response.headers.get("Content-Length", "")
                    if declared.isdigit() and int(declared) > self.settings.max_response_bytes:
                        return outcome(error="response_too_large")
                    body = bytearray()
                    for part in response.iter_bytes():
                        if time.monotonic() >= deadline:
                            return outcome(error="budget_exceeded")
                        if len(body) + len(part) > self.settings.max_response_bytes:
                            return outcome(error="response_too_large")
                        body.extend(part)
                    data = json.loads(body, parse_constant=_reject_non_json_number)
                    if type(data) is not dict:
                        raise ValueError("response must be a JSON object")
                    hits, truncated = self._hits(data, request.top_k)
                    if time.monotonic() >= deadline:
                        return outcome(error="budget_exceeded")
                    metadata["server_metadata"] = {
                        key: deepcopy(value) for key, value in data.items() if key != "documents"
                    }
                    metadata["truncated_results"] = truncated
                    return outcome("ok" if hits else "empty", results=hits)
            except httpx.TimeoutException:
                last_error = "timeout"
            except httpx.RequestError:
                last_error = "network_error"
            except (ValidationError, ValueError, TypeError, UnicodeError):
                return outcome(error="schema_error")
        if time.monotonic() >= deadline:
            return outcome(error="budget_exceeded")
        return outcome(error=last_error)
