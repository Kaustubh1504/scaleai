"""36. CSV upload endpoint with row validation: reference solution."""

import csv
import io
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile

REQUIRED = ("task_id", "annotator_email", "label", "submitted_at")
LABELS = ("negative", "neutral", "positive")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def to_utc(value: str) -> str | None:
    try:
        dt = datetime.fromisoformat(value)  # Python 3.11+ accepts a trailing "Z"
    except ValueError:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt.tzinfo else None


def create_app(storage_dir: str | Path) -> FastAPI:
    uploads = Path(storage_dir) / "uploads"
    app = FastAPI()

    @app.post("/uploads", status_code=201)
    async def upload(file: UploadFile) -> dict:
        if not (file.filename or "").lower().endswith(".csv"):
            raise HTTPException(415, "only .csv files are accepted")
        try:
            text = (await file.read()).decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(400, "file is not valid UTF-8")
        rows = [r for r in csv.reader(io.StringIO(text)) if r]
        if not rows:
            raise HTTPException(400, "file is empty: expected a header row")
        header = [h.strip().lower() for h in rows[0]]
        missing = [c for c in REQUIRED if c not in header]
        if missing:
            raise HTTPException(400, "missing required columns: " + ", ".join(missing))

        valid, errors, seen = [], [], set()
        for n, values in enumerate(rows[1:], 1):
            if len(values) != len(header):
                message = f"expected {len(header)} fields, got {len(values)}"
                errors.append({"row": n, "field": None, "message": message})
                continue
            v = dict(zip(header, map(str.strip, values)))
            task_id, email, label = v["task_id"], v["annotator_email"].lower(), v["label"].lower()
            ts = to_utc(v["submitted_at"])
            rules = [
                ("task_id", not task_id, "required"),
                ("task_id", task_id in seen, "duplicate task_id"),
                ("annotator_email", not email, "required"),
                ("annotator_email", not EMAIL_RE.match(email), "invalid email"),
                ("label", not label, "required"),
                ("label", label not in LABELS, "must be one of: " + ", ".join(LABELS)),
                ("submitted_at", not v["submitted_at"], "required"),
                ("submitted_at", ts is None, "invalid timestamp"),
            ]
            failed = next(((field, msg) for field, bad, msg in rules if bad), None)
            if failed:
                errors.append({"row": n, "field": failed[0], "message": failed[1]})
            else:
                seen.add(task_id)
                valid.append({"task_id": task_id, "annotator_email": email,
                              "label": label, "submitted_at": ts})

        summary = {"upload_id": uuid.uuid4().hex, "filename": file.filename,
                   "total_rows": len(rows) - 1, "valid_rows": len(valid),
                   "invalid_rows": len(errors), "errors": errors}
        uploads.mkdir(parents=True, exist_ok=True)
        path = uploads / f"{summary['upload_id']}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({**summary, "rows": valid}))
        os.replace(tmp, path)
        return summary

    @app.get("/uploads/{upload_id}")
    def get_upload(upload_id: str) -> dict:
        path = uploads / f"{upload_id}.json"
        if not path.exists():
            raise HTTPException(404, "upload not found")
        return json.loads(path.read_text())

    return app


if __name__ == "__main__":
    import tempfile

    from fastapi.testclient import TestClient

    from problem_api import SAMPLE_CSV

    with tempfile.TemporaryDirectory() as tmp:
        client = TestClient(create_app(tmp))
        resp = client.post("/uploads", files={"file": ("batch.csv", SAMPLE_CSV, "text/csv")})
        print(resp.status_code, resp.json())
        print(client.get(f"/uploads/{resp.json()['upload_id']}").json()["rows"])
