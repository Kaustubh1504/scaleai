"""Ticket triage service.

Run:    uvicorn app.main:app --reload
Tests:  python -m pytest

Keep the ``create_app`` signature: the interviewer's tests build the app with
their own storage directory, LLM client and clock.
"""

from __future__ import annotations

import threading
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.classifier import TicketClassifier
from app.ingest import PARSERS, IngestError, ingest
from app.storage import Store
from mock_services.clock import Clock, RealClock
from mock_services.llm import make_llm


def create_app(
    storage_dir: Path | str = "storage",
    llm=None,
    clock: Clock | None = None,
    max_concurrency: int = 4,
) -> FastAPI:
    store = Store(Path(storage_dir))
    llm = llm or make_llm()
    clock = clock or RealClock()
    classifier = TicketClassifier(llm, clock)
    # One classification run per upload at a time, so re-runs cannot interleave.
    run_locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)

    app = FastAPI(title="Ticket triage")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/uploads", status_code=201)
    async def create_upload(file: UploadFile = File(...)) -> dict:
        filename = file.filename or ""
        suffix = Path(filename).suffix.lower()
        if suffix not in PARSERS:
            raise HTTPException(415, f"unsupported file type {suffix or '(none)'}; expected one of {sorted(PARSERS)}")
        try:
            result = ingest(suffix, await file.read())
        except IngestError as exc:
            raise HTTPException(400, str(exc)) from exc
        summary = {
            "upload_id": uuid.uuid4().hex,
            "filename": filename,
            "total_rows": result.total_rows,
            "valid_rows": len(result.tickets),
            "invalid_rows": len(result.errors),
            "errors": result.errors,
        }
        store.save_upload({**summary, "tickets": result.tickets})
        return summary

    def get_upload_or_404(upload_id: str) -> dict:
        upload = store.load_upload(upload_id)
        if upload is None:
            raise HTTPException(404, f"upload {upload_id} not found")
        return upload

    @app.get("/uploads/{upload_id}")
    def get_upload(upload_id: str) -> dict:
        return get_upload_or_404(upload_id)

    @app.post("/uploads/{upload_id}/classify")
    def classify_upload(upload_id: str) -> dict:
        tickets = get_upload_or_404(upload_id)["tickets"]
        with run_locks[upload_id]:
            previous = {r["ticket_id"]: r for r in (store.load_classifications(upload_id) or {}).get("results", [])}
            todo = [t for t in tickets if previous.get(t["ticket_id"], {}).get("status") != "classified"]
            with ThreadPoolExecutor(max_workers=max(1, max_concurrency)) as pool:
                fresh = {r["ticket_id"]: r for r in pool.map(classifier.classify, todo)}
            results = [fresh.get(t["ticket_id"]) or previous[t["ticket_id"]] for t in tickets]
            doc = {
                "upload_id": upload_id,
                "classified": sum(r["status"] == "classified" for r in results),
                "failed": sum(r["status"] == "failed" for r in results),
                "results": results,
            }
            store.save_classifications(doc)
        return doc

    @app.get("/uploads/{upload_id}/classifications")
    def get_classifications(upload_id: str) -> dict:
        get_upload_or_404(upload_id)
        doc = store.load_classifications(upload_id)
        if doc is None:
            raise HTTPException(404, f"upload {upload_id} has not been classified")
        return doc

    return app


app = create_app()
