"""Task intake service.

Run:    uvicorn app.main:app --reload
Tests:  python -m pytest

Keep the ``create_app`` signature: the interviewer's tests build the app with
their own storage directory, clock and tenant configuration.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import parse_config
from app.intake import Intake
from app.models import TaskIn, valid_idempotency_key
from app.ratelimit import RateLimiter
from app.store import Store
from mock_services.clock import Clock, RealClock

DEFAULT_TENANTS_FILE = Path(__file__).resolve().parent.parent / "data" / "tenants.json"


def load_tenants(path: Path | str = DEFAULT_TENANTS_FILE) -> dict:
    """Read the plans + tenants config (shape: see data/tenants.json)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def create_app(
    storage_dir: Path | str = "storage",
    clock: Clock | None = None,
    tenants: dict | None = None,
) -> FastAPI:
    storage_dir = Path(storage_dir)
    clock = clock or RealClock()
    config = parse_config(tenants if tenants is not None else load_tenants())
    store = Store(storage_dir)
    intake = Intake(store, RateLimiter(clock), clock)

    app = FastAPI(title="Task intake")

    # Dependencies run in declaration order and before the body is validated,
    # which gives the spec's order of checks: tenant -> key -> body.
    def tenant_id(x_tenant_id: str | None = Header(None)) -> str:
        if not x_tenant_id:
            raise HTTPException(400, "missing X-Tenant-Id header")
        if config.plan_for(x_tenant_id) is None:
            raise HTTPException(403, "unknown tenant")
        return x_tenant_id

    def idempotency_key(idempotency_key: str | None = Header(None)) -> str | None:
        if idempotency_key is not None and not valid_idempotency_key(idempotency_key):
            raise HTTPException(400, "Idempotency-Key must be 1-64 characters of [A-Za-z0-9_-]")
        return idempotency_key

    async def raw_body(request: Request) -> bytes:
        return await request.body()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/tasks")
    def create_task(
        tenant: str = Depends(tenant_id),
        key: str | None = Depends(idempotency_key),
        body: bytes = Depends(raw_body),
    ) -> JSONResponse:
        try:
            task = TaskIn.model_validate_json(body)
        except ValidationError as exc:
            raise RequestValidationError(exc.errors(include_url=False)) from exc
        out = intake.create(tenant, config.plan_for(tenant), key, task)
        headers = {}
        if out.remaining is not None:
            headers["X-RateLimit-Remaining"] = str(out.remaining)
        if out.replayed:
            headers["Idempotent-Replayed"] = "true"
        if out.retry_after is not None:
            headers["Retry-After"] = str(out.retry_after)
        return JSONResponse(out.body, status_code=out.status, headers=headers)

    @app.get("/tasks")
    def list_tasks(tenant: str = Depends(tenant_id)) -> dict:
        return {"tasks": store.list_tasks(tenant)}

    @app.get("/tasks/{task_id}")
    def get_task(task_id: str, tenant: str = Depends(tenant_id)) -> dict:
        task = store.get_task(tenant, task_id)
        if task is None:
            raise HTTPException(404, "task not found")
        return task

    return app


app = create_app()
