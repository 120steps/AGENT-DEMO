"""Authenticated local single-process API; no public deployment or formal publication."""

import asyncio
import base64
import hmac
import json
import os
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from threading import BoundedSemaphore, Lock
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from agent_demo.domain.requirements import Requirement
from agent_demo.domain.reviews import ReviewResponse
from agent_demo.soc.rfp import ClauseMapping, confirm_requirements, parse_rfp
from agent_demo.soc.service import SOCService, TaskNotFound, service_from_environment


class SubmitTask(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    source_type: str = Field(pattern=r"^(mock|real_rag)$")
    requirements: list[Requirement] = Field(min_length=1, max_length=100)
    configuration: dict[str, str] = Field(default_factory=dict)
    input_confirmed: StrictBool = False


class PDFInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    pdf_base64: str = Field(min_length=1, max_length=14_000_000)


class PDFMapping(PDFInput):
    model: str
    mappings: list[ClauseMapping]
    excluded: dict[str, str] = Field(default_factory=dict)
    confirmed: StrictBool = False


class TaskView(BaseModel):
    task_id: str
    status: str = Field(pattern=r"^(pending|running|awaiting_review|completed|failed|cancelled)$")
    error_type: str | None
    source_type: str
    audit: dict
    review_snapshot: dict | None
    business_result: dict | None
    created_at: str
    updated_at: str


def create_app(*, service: SOCService | None = None, tokens=None, requests_per_minute=60):
    tokens = tokens if tokens is not None else json.loads(os.getenv("AGENT_DEMO_API_TOKENS", "{}"))
    if (
        not isinstance(tokens, dict)
        or not tokens
        or any(
            not isinstance(owner, str)
            or not owner
            or len(owner) > 128
            or not isinstance(token, str)
            or len(token) < 24
            or not token.isascii()
            for owner, token in tokens.items()
        )
        or len(set(tokens.values())) != len(tokens)
    ):
        raise ValueError("configure unique owner/token pairs, tokens at least 24 characters")
    service = service or service_from_environment(Path(os.getenv("AGENT_DEMO_DATA_ROOT", ".")))
    rate_lock, admitted = Lock(), BoundedSemaphore(4)
    buckets = defaultdict(deque)

    @asynccontextmanager
    async def lifespan(app):
        app.state.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="soc-local-task")
        yield
        app.state.executor.shutdown(wait=True, cancel_futures=True)

    app = FastAPI(title="AGENT-DEMO local SOC", lifespan=lifespan)
    bearer = HTTPBearer(auto_error=False)

    def owner(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if (
            credentials is None
            or credentials.scheme.lower() != "bearer"
            or not credentials.credentials.isascii()
        ):
            raise HTTPException(401, "authentication_required")
        name = next(
            (
                name
                for name, value in tokens.items()
                if hmac.compare_digest(value, credentials.credentials)
            ),
            None,
        )
        if name is None:
            raise HTTPException(401, "invalid_credentials")
        with rate_lock:
            recent = buckets[name]
            while recent and recent[0] < perf_counter() - 60:
                recent.popleft()
            if len(recent) >= requests_per_minute:
                raise HTTPException(429, "rate_limit")
            recent.append(perf_counter())
        return name

    @app.middleware("http")
    async def bounded_body(request, call_next):
        size, body = 0, bytearray()
        try:
            async with asyncio.timeout(15):
                async for part in request.stream():
                    size += len(part)
                    if size > 15_000_000:
                        return JSONResponse({"error_type": "request_too_large"}, status_code=413)
                    body.extend(part)
        except TimeoutError:
            return JSONResponse({"error_type": "request_read_timeout"}, status_code=408)
        request._body = bytes(body)
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, error):
        return JSONResponse({"error_type": "invalid_request"}, status_code=422)

    @app.exception_handler(TaskNotFound)
    async def not_found(request, error):
        return JSONResponse({"error_type": "unknown_task"}, status_code=404)

    @app.exception_handler(ValueError)
    async def conflict(request, error):
        return JSONResponse({"error_type": "invalid_operation"}, status_code=409)

    def enqueue(app, task_id, name, *, reserved=False):
        if not reserved and not admitted.acquire(blocking=False):
            raise HTTPException(429, "task_queue_full")
        try:
            future = app.state.executor.submit(service.run, task_id, name)
        except Exception:
            admitted.release()
            raise
        future.add_done_callback(lambda _: admitted.release())

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "execution_mode": "local_single_worker",
            "formal_publication": False,
        }

    @app.post("/tasks", status_code=202)
    def submit(payload: SubmitTask, request: Request, name=Depends(owner)):
        if not admitted.acquire(blocking=False):
            raise HTTPException(429, "task_queue_full")
        try:
            task = service.submit(payload.model_dump(mode="json"), name)
        except Exception:
            admitted.release()
            raise
        enqueue(request.app, task, name, reserved=True)
        return {"task_id": task, "status": "pending"}

    @app.get("/tasks/{task_id}", response_model=TaskView)
    def status(task_id: str, name=Depends(owner)):
        return service.status(task_id, name)

    @app.post("/tasks/{task_id}/run", status_code=202)
    def run(task_id: str, request: Request, name=Depends(owner)):
        service.get(task_id, name)
        enqueue(request.app, task_id, name)
        return {"task_id": task_id, "status": "scheduled"}

    @app.post("/tasks/{task_id}/review", response_model=TaskView)
    def review(task_id: str, payload: ReviewResponse, name=Depends(owner)):
        return service.review(task_id, name, payload.model_dump(mode="json", exclude_none=True))

    @app.post("/tasks/{task_id}/cancel")
    def cancel(task_id: str, name=Depends(owner)):
        return service.cancel(task_id, name)

    @app.get("/tasks/{task_id}/result")
    def result(task_id: str, draft: bool = False, name=Depends(owner)):
        artifact = service.export(task_id, name, draft=draft)
        return FileResponse(
            artifact["path"],
            filename=f"soc-{task_id}-DRAFT.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def pdf(payload):
        try:
            return parse_rfp(base64.b64decode(payload.pdf_base64, validate=True))
        except Exception:
            raise HTTPException(422, "invalid_or_unsupported_pdf") from None

    @app.post("/rfp/parse")
    def parse(payload: PDFInput, name=Depends(owner)):
        return pdf(payload)

    @app.post("/rfp/confirm")
    def confirm(payload: PDFMapping, name=Depends(owner)):
        document = pdf(payload)
        requirements = confirm_requirements(
            document,
            payload.model,
            [m.model_dump(mode="json") for m in payload.mappings],
            excluded=payload.excluded,
            confirmed=payload.confirmed,
        )
        return {"source_type": "real_rag", "requirements": requirements, "input_confirmed": True}

    return app
