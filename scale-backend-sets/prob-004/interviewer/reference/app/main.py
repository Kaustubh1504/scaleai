"""Annotation task service.

Run:    uvicorn --factory app.main:create_app --reload   (stores data in ./storage)
Tests:  python -m pytest

Keep the ``create_app`` signature: the interviewer's tests build the app with
their own storage directory, clock, lease length and redundancy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.db import LabelNotAllowed, LeaseConflict, TaskNotFound, TaskStore
from app.models import SubmitRequest, TaskBatch, parse_entry
from mock_services.clock import Clock, RealClock

ERROR_STATUS = {TaskNotFound: 404, LeaseConflict: 409, LabelNotAllowed: 422}


def annotator_id(x_annotator_id: Annotated[str | None, Header()] = None) -> str:
    if x_annotator_id is None or not x_annotator_id.strip():
        raise HTTPException(400, "X-Annotator-Id header is required")
    return x_annotator_id.strip()


Annotator = Annotated[str, Depends(annotator_id)]


def create_app(
    storage_dir: Path | str = "storage",
    clock: Clock | None = None,
    lease_seconds: float = 60,
    redundancy: int = 1,
) -> FastAPI:
    """Build the app. Each task needs ``redundancy`` submissions from distinct annotators."""
    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")
    if redundancy < 1:
        raise ValueError("redundancy must be at least 1")
    storage_dir = Path(storage_dir)
    clock = clock or RealClock()
    store = TaskStore(storage_dir / "tasks.db", clock=clock, lease_seconds=lease_seconds, redundancy=redundancy)

    app = FastAPI(title="Annotation tasks")

    for error, status in ERROR_STATUS.items():
        def handler(request: Request, exc: Exception, status: int = status) -> JSONResponse:
            return JSONResponse({"detail": str(exc)}, status_code=status)

        app.add_exception_handler(error, handler)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "time": clock.time()}

    @app.post("/tasks", status_code=201)
    def create_tasks(batch: TaskBatch) -> dict:
        valid, errors = [], []
        for index, entry in enumerate(batch.tasks):
            task, error = parse_entry(entry)
            if task is None:
                errors.append({"index": index, "error": error})
            else:
                valid.append((index, task))
        created, duplicate_errors = store.create_tasks(valid)
        errors = sorted(errors + duplicate_errors, key=lambda e: e["index"])
        return {"created": created, "errors": errors}

    @app.get("/tasks")
    def list_tasks(state: str | None = None) -> dict:
        return {"tasks": store.list_tasks(state)}

    @app.get("/tasks/{task_id}")
    def get_task(task_id: str) -> dict:
        task = store.get_task(task_id)
        if task is None:
            raise HTTPException(404, f"task {task_id} not found")
        return task

    @app.post("/tasks/claim")
    def claim_task(annotator: Annotator):
        task = store.claim(annotator)
        if task is None:
            return Response(status_code=204)
        return task

    @app.post("/tasks/{task_id}/extend")
    def extend_lease(task_id: str, annotator: Annotator) -> dict:
        return store.extend(task_id, annotator)

    @app.post("/tasks/{task_id}/submit")
    def submit_task(task_id: str, body: SubmitRequest, annotator: Annotator) -> dict:
        return store.submit(task_id, annotator, body.label)

    @app.get("/annotators/{annotator}/stats")
    def annotator_stats(annotator: str) -> dict:
        return store.annotator_stats(annotator)

    return app
