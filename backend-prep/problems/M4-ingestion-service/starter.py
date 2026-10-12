"""M4. Ingestion service

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import json
import queue
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from problem_api import RetryableError

MAX_ATTEMPTS = 3
SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY, seq INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS rows (
    batch_id TEXT NOT NULL, idx INTEGER NOT NULL, row_id TEXT NOT NULL, text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', label TEXT, attempts INTEGER NOT NULL DEFAULT 0, error TEXT,
    job_id TEXT, PRIMARY KEY (batch_id, idx));
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY, batch_id TEXT NOT NULL, status TEXT NOT NULL, total INTEGER NOT NULL, seq INTEGER NOT NULL);
"""


def parse_jsonl(raw: bytes) -> tuple[list[dict], list[dict]]:
    raise NotImplementedError


class Service:
    def __init__(self, storage_dir: str | Path, classifier: Callable[[str], str] | None):
        Path(storage_dir).mkdir(parents=True, exist_ok=True)
        self.db_path = Path(storage_dir) / "ingest.db"
        self.classifier = classifier
        self._lock = threading.Lock()               # one writer at a time: no "database is locked"
        self._jobs: queue.Queue[str] = queue.Queue()
        with self.db() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.executescript(SCHEMA)
            unfinished = con.execute("SELECT id FROM jobs WHERE status IN ('queued', 'running') ORDER BY seq")
            for (job_id,) in unfinished.fetchall():
                self._jobs.put(job_id)              # restart: resume where the last process stopped
        threading.Thread(target=self._work, name="ingest-worker", daemon=True).start()

    @contextmanager
    def db(self) -> Iterator[sqlite3.Connection]:
        raise NotImplementedError

    def create_batch(self, rows: list[dict]) -> str:
        raise NotImplementedError

    def batch(self, batch_id: str) -> dict | None:
        raise NotImplementedError

    def rows(self, batch_id: str) -> list[dict]:
        raise NotImplementedError

    def start_job(self, batch_id: str) -> tuple[int, dict]:
        raise NotImplementedError

    def job(self, job_id: str) -> dict | None:
        raise NotImplementedError


def create_app(storage_dir: str | Path, classifier: Callable[[str], str] | None = None) -> FastAPI:
    app = FastAPI(title="Ingestion service")
    svc = Service(storage_dir, classifier)
    app.state.service = svc

    @app.post("/batches", status_code=201)
    def upload(file: UploadFile = File(...)):
        raise NotImplementedError

    @app.get("/batches/{batch_id}")
    def get_batch(batch_id: str):
        raise NotImplementedError

    @app.get("/batches/{batch_id}/rows")
    def get_rows(batch_id: str):
        raise NotImplementedError

    @app.post("/batches/{batch_id}/process")
    def process(batch_id: str):
        raise NotImplementedError

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str):
        raise NotImplementedError

    return app


if __name__ == "__main__":
    import tempfile
    import time

    from fastapi.testclient import TestClient

    from problem_api import SAMPLE_JSONL, flaky_classifier

    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(create_app(tmp, flaky_classifier())) as client:
            up = client.post("/batches", files={"file": ("rows.jsonl", SAMPLE_JSONL.read_bytes())}).json()
            print("upload:", up)
            job = client.post(f"/batches/{up['batch_id']}/process").json()
            while client.get(f"/jobs/{job['job_id']}").json()["status"] != "completed":
                time.sleep(0.01)
            print("job:", client.get(f"/jobs/{job['job_id']}").json())
            for row in client.get(f"/batches/{up['batch_id']}/rows").json()["rows"]:
                print(row)
            print("again:", client.post(f"/batches/{up['batch_id']}/process").json())
