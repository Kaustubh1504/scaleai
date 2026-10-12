"""36. CSV upload endpoint with row validation

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import csv
import io
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, File, HTTPException, UploadFile

REQUIRED = ("task_id", "annotator_email", "label", "submitted_at")
LABELS = ("negative", "neutral", "positive")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
UPLOAD_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def parse_ts(s: str) -> str | None:
    """UTC 'YYYY-MM-DDTHH:MM:SSZ', or None if the value isn't an offset-aware ISO 8601 datetime."""
    if s.endswith(("Z", "z")):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt.tzinfo else None


def check(v, seen):
    """(field, message) for the first rule that fails, else None."""
    if not v["task_id"]: return "task_id", "required"
    if v["task_id"] in seen: return "task_id", "duplicate task_id"
    if not v["annotator_email"]: return "annotator_email", "required"
    if not EMAIL_RE.match(v["annotator_email"]): return "annotator_email", "invalid email"
    if not v["label"]: return "label", "required"
    if v["label"] not in LABELS: return "label", "must be one of: " + ", ".join(LABELS)
    if not v["submitted_at"]: return "submitted_at", "required"
    if not parse_ts(v["submitted_at"]): return "submitted_at", "invalid timestamp"
    return None

def create_app(storage_dir: str | Path) -> FastAPI:
    uploads = Path(storage_dir) / "uploads"
    app = FastAPI(title="Annotation uploads")

    @app.post("/uploads", status_code=201)
    async def upload(file: UploadFile = File(...)) -> dict:
        name = file.filename or ""
        if not name.lower().endswith(".csv"):
            raise HTTPException(415, "only .csv files are accepted")
        try:
            text = (await file.read()).decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(400, "file is not valid UTF-8")
        rows = [r for r in csv.reader(io.StringIO(text)) if r]   # [] = blank line
        if not rows:
            raise HTTPException(400, "file is empty: expected a header row")
        header = [h.strip().lower() for h in rows[0]]
        missing = [c for c in REQUIRED if c not in header]
        if missing:
            raise HTTPException(400, "missing required columns: " + ", ".join(missing))
            
        
        valid, errors, seen = [], [], set()
        for n, values in enumerate(rows[1:], start=1):
            if len(values) != len(header):
                errors.append({"row": n, "field": None,
                               "message": f"expected {len(header)} fields, got {len(values)}"})
                continue
            v = {c: values[header.index(c)].strip() for c in REQUIRED}
            v["label"] = v["label"].lower()
            v["annotator_email"] = v["annotator_email"].lower()
            err = check(v, seen)
            if err:
                errors.append({"row": n, "field": err[0], "message": err[1]})
            else:
                seen.add(v["task_id"])
                v["submitted_at"] = parse_ts(v["submitted_at"])
                valid.append(v)
 
        summary = {"upload_id": uuid.uuid4().hex, "filename": name,
                   "total_rows": len(rows) - 1, "valid_rows": len(valid),
                   "invalid_rows": len(errors), "errors": errors}
        uploads.mkdir(parents=True, exist_ok=True)
        (uploads / f"{summary['upload_id']}.json").write_text(json.dumps({**summary, "rows": valid}))
        return summary
        
            

    @app.get("/uploads/{upload_id}")
    def get_upload(upload_id: str) -> dict:
        path = uploads / f"{upload_id}.json"
        if not re.fullmatch(r"[0-9a-f]{32}", upload_id) or not path.exists():
            raise HTTPException(404, "upload not found")
        return json.loads(path.read_text())

    return app


if __name__ == "__main__":
    import tempfile
    import warnings

    warnings.filterwarnings("ignore", message="Using `httpx`")  # starlette TestClient notice
    from fastapi.testclient import TestClient

    from problem_api import SAMPLE_CSV

    with tempfile.TemporaryDirectory() as tmp:
        client = TestClient(create_app(tmp))
        resp = client.post("/uploads", files={"file": ("batch.csv", SAMPLE_CSV, "text/csv")})
        print(resp.status_code, json.dumps(resp.json(), indent=2))
        resp = client.get(f"/uploads/{resp.json()['upload_id']}")
        print(resp.status_code, resp.json()["rows"])
        print(client.post("/uploads", files={"file": ("batch.txt", b"x", "text/plain")}).json())
