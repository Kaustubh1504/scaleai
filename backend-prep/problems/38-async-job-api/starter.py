"""38. Async job API with background workers

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import queue
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Literal, Optional
from fastapi import Body, FastAPI, HTTPException

KINDS = ("word_count", "sum")
Status = Literal["queued", "running", "done", "failed"]


def run_job(payload: dict) -> Any:
    raise NotImplementedError


class JobStore:
    """The job table. Every access holds the lock; callers only ever get copies."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, dict] = {}  # insertion order == submission order

    def add(self, payload: dict) -> str:
        raise NotImplementedError

    def update(self, job_id: str, **fields: Any) -> None:
        raise NotImplementedError

    def payload(self, job_id: str) -> dict:
        raise NotImplementedError

    def get(self, job_id: str) -> dict | None:
        raise NotImplementedError

    def list(self, status: str | None = None) -> list[dict]:
        raise NotImplementedError


def create_app(storage_dir: str | Path | None = None, workers: int = 2,
               process: Callable[[dict], Any] | None = None) -> FastAPI:
    process = process or run_job
    store = JobStore()
    pending: queue.Queue[str | None] = queue.Queue()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        raise NotImplementedError

    app = FastAPI(title="Jobs", lifespan=lifespan)

    @app.post("/jobs", status_code=202)
    def submit(payload: dict = Body(...)) -> dict:
        raise NotImplementedError

    @app.get("/jobs")
    def list_jobs(status: Optional[Status] = None) -> dict:
        raise NotImplementedError

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        raise NotImplementedError

    return app


if __name__ == "__main__":
    import time
    import warnings

    warnings.filterwarnings("ignore", message="Using `httpx`")  # starlette TestClient notice
    from fastapi.testclient import TestClient

    with TestClient(create_app(workers=2)) as c:
        ids = [c.post("/jobs", json=body).json()["job_id"] for body in (
            {"kind": "word_count", "text": "the quick  brown\nfox"},
            {"kind": "sum", "numbers": [1, 2, 3.5]},
            {"kind": "sum", "numbers": ["oops"]},
        )]
        print("422:", c.post("/jobs", json={"kind": "resize"}).status_code)
        deadline = time.time() + 5
        while time.time() < deadline and c.get("/jobs", params={"status": "queued"}).json()["jobs"] + \
                c.get("/jobs", params={"status": "running"}).json()["jobs"]:
            time.sleep(0.01)
        for job_id in ids:
            print(c.get(f"/jobs/{job_id}").json())
