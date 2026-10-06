"""Annotation task service.

Run:    uvicorn --factory app.main:create_app --reload   (stores data in ./storage)
Tests:  python -m pytest

Keep the ``create_app`` signature: the interviewer's tests build the app with
their own storage directory, clock, lease length and redundancy.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Response

from app.db import TaskStore
from app.models import SubmitRequest, TaskBatch, parse_entry
from mock_services.clock import Clock, RealClock


def create_app(
    storage_dir: Path | str = "storage",
    clock: Clock | None = None,
    lease_seconds: float = 60,
    redundancy: int = 1,
) -> FastAPI:
    """Build the app.

    ``lease_seconds`` and ``redundancy`` are configuration for the leasing
    work on the roadmap; nothing reads them yet.
    """
    storage_dir = Path(storage_dir)
    clock = clock or RealClock()
    store = TaskStore(storage_dir / "tasks.db")

    app = FastAPI(title="Annotation tasks")

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
    def claim_task(x_annotator_id: str = Header(...)):
        task = store.oldest_pending()
        if task is None:
            return Response(status_code=204)
        return task

    @app.post("/tasks/{task_id}/submit")
    def submit_task(task_id: str, body: SubmitRequest, x_annotator_id: str = Header(...)) -> dict:
        task = store.get_task(task_id)
        if task is None:
            raise HTTPException(404, f"task {task_id} not found")
        if task["state"] == "submitted":
            raise HTTPException(409, f"task {task_id} is already submitted")
        if body.label not in task["labels"]:
            raise HTTPException(422, f"label {body.label!r} is not one of {task['labels']}")
        store.record_submission(task_id, x_annotator_id, body.label)
        store.set_state(task_id, "submitted")
        return store.get_task(task_id)

    return app
