"""M4. Ingestion service: reference solution."""

from __future__ import annotations

import json
import queue
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from problem_api import RetryableError

MAX_ATTEMPTS = 3

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS rows (
    batch_id TEXT, idx INTEGER, row_id TEXT, text TEXT, status TEXT DEFAULT 'pending',
    label TEXT, attempts INTEGER DEFAULT 0, error TEXT, job_id TEXT, PRIMARY KEY (batch_id, idx));
CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, batch_id TEXT, status TEXT, total INTEGER);
"""

# ------------------------------------------------------------------ Part 1: parsing


def parse_jsonl(raw: bytes) -> tuple[list[dict], list[dict]]:
    text = raw.decode("utf-8")
    rows, errors, seen = [], [], set()
    for n, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            errors.append({"line": n, "error": "invalid_json"})
            continue
        if not isinstance(obj, dict):
            error = "not_an_object"
        elif not isinstance(obj.get("id"), str) or not obj["id"].strip():
            error = "missing_id"
        elif not isinstance(obj.get("text"), str) or not obj["text"].strip():
            error = "missing_text"
        elif obj["id"] in seen:
            error = "duplicate_id"
        else:
            seen.add(obj["id"])
            rows.append({"id": obj["id"], "text": obj["text"]})
            continue
        errors.append({"line": n, "error": error})
    return rows, errors


# ------------------------------------------------------------------ storage + worker


class Service:
    def __init__(self, storage_dir: str | Path, classifier: Callable[[str], str] | None):
        Path(storage_dir).mkdir(parents=True, exist_ok=True)
        self.db_path = Path(storage_dir) / "ingest.db"
        self.classifier = classifier
        self.lock = threading.Lock()  # one connection at a time: no "database is locked"
        self.jobs = queue.Queue()
        with self.db() as con:
            con.executescript(SCHEMA)
            for (job_id,) in con.execute(
                    "SELECT id FROM jobs WHERE status IN ('queued', 'running') ORDER BY rowid"):
                self.jobs.put(job_id)
        threading.Thread(target=self.work, daemon=True).start()

    @contextmanager
    def db(self):
        with self.lock:
            con = sqlite3.connect(self.db_path)
            try:
                with con:
                    yield con
            finally:
                con.close()

    def create_batch(self, rows: list[dict]) -> str:
        batch_id = f"b_{uuid.uuid4().hex[:12]}"
        with self.db() as con:
            con.execute("INSERT INTO batches VALUES (?)", (batch_id,))
            con.executemany("INSERT INTO rows (batch_id, idx, row_id, text) VALUES (?, ?, ?, ?)",
                            [(batch_id, i, r["id"], r["text"]) for i, r in enumerate(rows)])
        return batch_id

    def batch(self, batch_id: str) -> dict | None:
        with self.db() as con:
            if not con.execute("SELECT 1 FROM batches WHERE id = ?", (batch_id,)).fetchone():
                return None
            counts = dict(con.execute("SELECT status, COUNT(*) FROM rows WHERE batch_id = ? "
                                      "GROUP BY status", (batch_id,)))
        counts = {s: counts.get(s, 0) for s in ("pending", "done", "failed")}
        return {"batch_id": batch_id, "row_count": sum(counts.values()), "counts": counts}

    def rows(self, batch_id: str) -> list[dict]:
        keys = ("id", "text", "status", "label", "attempts", "error")
        with self.db() as con:
            cur = con.execute("SELECT row_id, text, status, label, attempts, error FROM rows "
                              "WHERE batch_id = ? ORDER BY idx", (batch_id,))
            return [dict(zip(keys, r)) for r in cur]

    def start_job(self, batch_id: str) -> tuple[int, dict]:
        with self.db() as con:  # check-and-create under one lock: one job per batch
            active = con.execute("SELECT id FROM jobs WHERE batch_id = ? "
                                 "AND status IN ('queued', 'running')", (batch_id,)).fetchone()
            if active:
                return 200, self._job(con, active[0])
            pending = con.execute("SELECT COUNT(*) FROM rows WHERE batch_id = ? AND status = 'pending'",
                                  (batch_id,)).fetchone()[0]
            if pending == 0:
                return 200, {"job_id": None, "status": "nothing_to_do"}
            job_id = f"j_{uuid.uuid4().hex[:12]}"
            con.execute("INSERT INTO jobs VALUES (?, ?, 'queued', ?)", (job_id, batch_id, pending))
            con.execute("UPDATE rows SET job_id = ? WHERE batch_id = ? AND status = 'pending'",
                        (job_id, batch_id))
            job = self._job(con, job_id)
        self.jobs.put(job_id)
        return 202, job

    def job(self, job_id: str) -> dict | None:
        with self.db() as con:
            return self._job(con, job_id)

    def _job(self, con: sqlite3.Connection, job_id: str) -> dict | None:
        row = con.execute("SELECT batch_id, status, total FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        counts = dict(con.execute("SELECT status, COUNT(*) FROM rows WHERE job_id = ? GROUP BY status",
                                  (job_id,)))
        return {"job_id": job_id, "batch_id": row[0], "status": row[1], "total": row[2],
                "done": counts.get("done", 0), "failed": counts.get("failed", 0)}

    # -------------------------------------------------------------- Part 2: worker

    def work(self) -> None:
        while True:
            job_id = self.jobs.get()
            with self.db() as con:
                con.execute("UPDATE jobs SET status = 'running' WHERE id = ?", (job_id,))
            while True:
                with self.db() as con:
                    nxt = con.execute("SELECT batch_id, idx, text FROM rows WHERE job_id = ? "
                                      "AND status = 'pending' ORDER BY idx LIMIT 1", (job_id,)).fetchone()
                if nxt is None:
                    break
                batch_id, idx, text = nxt
                for attempt in range(1, MAX_ATTEMPTS + 1):  # classify outside the DB lock
                    try:
                        status, label, error = "done", self.classifier(text), None
                        break
                    except Exception as exc:
                        status, label, error = "failed", None, str(exc)
                        if not isinstance(exc, RetryableError):
                            break
                with self.db() as con:
                    con.execute("UPDATE rows SET status = ?, label = ?, attempts = ?, error = ? "
                                "WHERE batch_id = ? AND idx = ?",
                                (status, label, attempt, error, batch_id, idx))
            with self.db() as con:
                con.execute("UPDATE jobs SET status = 'completed' WHERE id = ?", (job_id,))


# ------------------------------------------------------------------ HTTP


def create_app(storage_dir: str | Path, classifier: Callable[[str], str] | None = None) -> FastAPI:
    app = FastAPI()
    svc = app.state.service = Service(storage_dir, classifier)

    def get_batch_or_404(batch_id: str) -> dict:
        batch = svc.batch(batch_id)
        if batch is None:
            raise HTTPException(404, "batch not found")
        return batch

    @app.post("/batches", status_code=201)
    def upload(file: UploadFile = File(...)):
        try:
            rows, errors = parse_jsonl(file.file.read())
        except UnicodeDecodeError:
            raise HTTPException(400, "file must be UTF-8")
        if not rows:
            return JSONResponse({"detail": "no valid rows", "errors": errors}, status_code=422)
        return {"batch_id": svc.create_batch(rows), "accepted": len(rows),
                "rejected": len(errors), "errors": errors}

    @app.get("/batches/{batch_id}")
    def get_batch(batch_id: str):
        return get_batch_or_404(batch_id)

    @app.get("/batches/{batch_id}/rows")
    def get_rows(batch_id: str):
        get_batch_or_404(batch_id)
        return {"rows": svc.rows(batch_id)}

    @app.post("/batches/{batch_id}/process")
    def process(batch_id: str):
        get_batch_or_404(batch_id)
        status, body = svc.start_job(batch_id)
        return JSONResponse(body, status_code=status)

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str):
        job = svc.job(job_id)
        if job is None:
            raise HTTPException(404, "job not found")
        return job

    return app


if __name__ == "__main__":
    import tempfile
    import time

    from fastapi.testclient import TestClient

    from problem_api import SAMPLE_JSONL, flaky_classifier

    with tempfile.TemporaryDirectory() as tmp, TestClient(create_app(tmp, flaky_classifier())) as client:
        up = client.post("/batches", files={"file": ("rows.jsonl", SAMPLE_JSONL.read_bytes())}).json()
        print("upload:", up)
        job = client.post(f"/batches/{up['batch_id']}/process").json()
        while client.get(f"/jobs/{job['job_id']}").json()["status"] != "completed":
            time.sleep(0.01)
        print("job:", client.get(f"/jobs/{job['job_id']}").json())
        print("rows:", client.get(f"/batches/{up['batch_id']}/rows").json()["rows"])
        print("again:", client.post(f"/batches/{up['batch_id']}/process").json())
