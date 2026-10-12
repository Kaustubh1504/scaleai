"""37. A task store that survives restarts

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import json
import os
import threading
from pathlib import Path
from typing import Literal, Optional
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


class TaskCreate(BaseModel):
    id: str = Field(pattern=ID_PATTERN)
    title: str = Field(min_length=1)
    assignee: Optional[str] = None


class TaskUpdate(BaseModel):
    title: str = Field(min_length=1)
    assignee: Optional[str] = None
    status: Literal["open", "done"] = "open"


class TaskStore:
    """All tasks in one JSON file, rewritten atomically on every change."""

    def __init__(self, storage_dir: str | Path):
        self.dir = Path(storage_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "tasks.json"
        self.lock = threading.Lock()  # def-handlers run in a thread pool
        self.tasks: dict[str, dict] = {}  # insertion order == creation order
        if self.path.exists():
            self.tasks = {t["id"]: t for t in json.loads(self.path.read_text())}

    def get(self, task_id: str) -> dict | None:
        raise NotImplementedError

    def all(self) -> list[dict]:
        raise NotImplementedError

    def create(self, body: TaskCreate) -> tuple[dict, bool]:
        """Returns (task, created). Raises HTTPException(409) on a conflicting re-create."""
        raise NotImplementedError

    def update(self, task_id: str, body: TaskUpdate) -> dict | None:
        raise NotImplementedError


def create_app(storage_dir: str | Path) -> FastAPI:
    store = TaskStore(storage_dir)
    app = FastAPI(title="Review tasks")

    @app.post("/tasks", status_code=201)
    def create_task(body: TaskCreate, response: Response) -> dict:
        raise NotImplementedError

    @app.get("/tasks")
    def list_tasks() -> dict:
        raise NotImplementedError

    @app.get("/tasks/{task_id}")
    def get_task(task_id: str) -> dict:
        raise NotImplementedError

    @app.put("/tasks/{task_id}")
    def update_task(task_id: str, body: TaskUpdate) -> dict:
        raise NotImplementedError

    return app


if __name__ == "__main__":
    import tempfile
    import warnings

    warnings.filterwarnings("ignore", message="Using `httpx`")  # starlette TestClient notice
    from fastapi.testclient import TestClient

    with tempfile.TemporaryDirectory() as tmp:
        c = TestClient(create_app(tmp))
        for body in ({"id": "t1", "title": "Review batch 7"}, {"id": "t1", "title": "Review batch 7"},
                     {"id": "t1", "title": "Something else"}):
            r = c.post("/tasks", json=body)
            print("POST", r.status_code, r.json())
        r = c.put("/tasks/t1", json={"title": "Review batch 7", "status": "done"})
        print("PUT ", r.status_code, r.json())
        c2 = TestClient(create_app(tmp))
        print("after restart:", c2.get("/tasks").json())
        print("files:", sorted(os.listdir(tmp)))
