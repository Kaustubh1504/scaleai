"""38. Async job API with background workers: reference solution."""

import queue
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Literal

from fastapi import Body, FastAPI, HTTPException


def run_job(payload: dict) -> Any:
    kind, text, numbers = payload.get("kind"), payload.get("text"), payload.get("numbers")
    if kind == "word_count" and isinstance(text, str):
        return len(text.split())
    if kind == "sum" and isinstance(numbers, list) and all(
            isinstance(n, (int, float)) and not isinstance(n, bool) for n in numbers):
        return sum(numbers)
    raise ValueError(f"invalid {kind!r} job")


def create_app(storage_dir: str | Path | None = None, workers: int = 2,
               process: Callable[[dict], Any] | None = None) -> FastAPI:
    process = process or run_job
    jobs: dict[str, dict] = {}
    lock = threading.Lock()  # guards inserts vs. iteration in list_jobs
    pending = queue.Queue()

    def worker() -> None:
        while (item := pending.get()) is not None:
            job_id, payload = item
            jobs[job_id]["status"] = "running"
            try:
                jobs[job_id].update(status="done", result=process(payload))
            except Exception as exc:
                jobs[job_id].update(status="failed", error=str(exc) or type(exc).__name__)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        threads = [threading.Thread(target=worker, daemon=True) for _ in range(workers)]
        for t in threads:
            t.start()
        yield
        for t in threads:
            pending.put(None)
        for t in threads:
            t.join()

    app = FastAPI(lifespan=lifespan)

    @app.post("/jobs", status_code=202)
    def submit(payload: dict = Body()) -> dict:
        if payload.get("kind") not in ("word_count", "sum"):
            raise HTTPException(422, "kind must be 'word_count' or 'sum'")
        job_id = uuid.uuid4().hex
        with lock:
            jobs[job_id] = {"job_id": job_id, "kind": payload.get("kind"), "status": "queued",
                            "result": None, "error": None}
        pending.put((job_id, payload))
        return {"job_id": job_id, "status": "queued"}

    @app.get("/jobs")
    def list_jobs(status: Literal["queued", "running", "done", "failed"] | None = None) -> dict:
        with lock:
            return {"jobs": [j for j in jobs.values() if status is None or j["status"] == status]}

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        if job_id not in jobs:
            raise HTTPException(404, "job not found")
        return jobs[job_id]

    return app


if __name__ == "__main__":
    import time

    from fastapi.testclient import TestClient

    with TestClient(create_app()) as c:
        ids = [c.post("/jobs", json=body).json()["job_id"] for body in (
            {"kind": "word_count", "text": "the quick  brown\nfox"},
            {"kind": "sum", "numbers": [1, 2, 3.5]},
            {"kind": "sum", "numbers": ["oops"]},
        )]
        print("422:", c.post("/jobs", json={"kind": "resize"}).status_code)
        time.sleep(0.2)
        for job_id in ids:
            print(c.get(f"/jobs/{job_id}").json())
