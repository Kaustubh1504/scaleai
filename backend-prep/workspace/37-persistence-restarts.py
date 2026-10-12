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



def create_app(storage_dir: str | Path) -> FastAPI:
    path = Path(storage_dir)/"tasks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tasks = {t["id"]: t for t in json.loads(path.read_text())} if path.exists() else {}
    lock = threading.Lock()
    app = FastAPI()
    
    def save():
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(list(tasks.values())))
        os.replace(tmp, path)
        
    @app.post("/tasks", status_code=201)
    def create_task(body: TaskCreate, response: Response) -> dict:
        with lock:
            if existing:= tasks.get(body.id):
                if (existing["title"], existing["assignee"]) != (body.title, body.assignee):
                    raise HTTPException(409, f"task {body.id!r} already exists with different fields")
                response.status_code = 200
                return existing
            tasks[body.id] = {**body.model_dump(), "status":"open"}
            save()
            return tasks[body.id]

    @app.get("/tasks")
    def list_tasks() -> dict:
        return {"tasks": list(tasks.values())}

    @app.get("/tasks/{task_id}")
    def get_task(task_id: str) -> dict:
        if task_id not in tasks:
            raise HTTPException(404, "task not found")
        return tasks[task_id]

    @app.put("/tasks/{task_id}")
    def update_task(task_id: str, body: TaskUpdate) -> dict:
        with lock:
            if task_id not in tasks:
                raise HTTPException(404, "task not found")
            tasks[task_id] = {"id": task_id, **body.model_dump()}
            save()
            return tasks[task_id]

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
