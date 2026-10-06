"""Document intake service.

Run:    uvicorn --factory app.main:create_app --reload   (stores data in ./storage)
Tests:  python -m pytest

Keep the ``create_app`` signature: the interviewer's tests build the app with
their own storage directory, LLM client, clock and settings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app.classifier import DocumentClassifier
from app.db import DocumentNotFound, DocumentStore, ReasonRequired, StatusConflict
from app.ingest import PARSERS, IngestError, parse_upload
from app.routing import INGESTED, route
from mock_services.clock import Clock, RealClock
from mock_services.llm import LABELS, make_llm

ERROR_STATUS = {DocumentNotFound: 404, StatusConflict: 409, ReasonRequired: 422}
Action = Literal["ingested", "classified", "auto_accepted", "routed_to_review", "reviewed"]


class ReviewRequest(BaseModel):
    reviewer: str
    label: str
    reason: str | None = None
    expected_version: int | None = None

    @field_validator("reviewer")
    @classmethod
    def _reviewer_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reviewer must not be blank")
        return value.strip()

    @field_validator("label")
    @classmethod
    def _label_allowed(cls, value: str) -> str:
        if value not in LABELS:
            raise ValueError(f"label must be one of {', '.join(LABELS)}")
        return value

    @field_validator("reason")
    @classmethod
    def _blank_reason_is_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


def create_app(
    storage_dir: Path | str = "storage",
    llm=None,
    clock: Clock | None = None,
    auto_accept_threshold: float = 0.8,
    consistency_samples: int = 1,
) -> FastAPI:
    """Build the app.

    Documents whose classification confidence is at least ``auto_accept_threshold``
    are auto-accepted; the rest go to the review queue. ``consistency_samples=2``
    classifies every document twice and sends disagreements to review.
    """
    if not 0 <= auto_accept_threshold <= 1:
        raise ValueError("auto_accept_threshold must be between 0 and 1")
    if consistency_samples not in (1, 2):
        raise ValueError("consistency_samples must be 1 or 2")
    clock = clock or RealClock()
    store = DocumentStore(Path(storage_dir) / "intake.db", clock=clock)
    classifier = DocumentClassifier(llm or make_llm())

    app = FastAPI(title="Document intake")

    for error, status in ERROR_STATUS.items():
        def handler(request: Request, exc: Exception, status: int = status) -> JSONResponse:
            return JSONResponse({"detail": str(exc)}, status_code=status)

        app.add_exception_handler(error, handler)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "time": clock.time()}

    @app.post("/batches", status_code=201)
    async def upload_batch(file: UploadFile = File(...)) -> dict:
        filename = file.filename or ""
        suffix = Path(filename).suffix.lower()
        if suffix not in PARSERS:
            raise HTTPException(415, f"unsupported file type {suffix or '(none)'}; expected one of {sorted(PARSERS)}")
        try:
            parsed = parse_upload(suffix, await file.read())
        except IngestError as exc:
            raise HTTPException(400, str(exc)) from exc
        return store.create_batch(filename, parsed.total_rows, parsed.documents, parsed.errors)

    def batch_or_404(batch_id: str) -> dict:
        batch = store.get_batch(batch_id)
        if batch is None:
            raise HTTPException(404, f"batch {batch_id} not found")
        return batch

    @app.get("/batches/{batch_id}")
    def get_batch(batch_id: str) -> dict:
        return batch_or_404(batch_id)

    @app.post("/batches/{batch_id}/classify")
    def classify_batch(batch_id: str) -> dict:
        """Classify and route the batch's ``ingested`` documents; routed ones are never touched again.

        The model is called outside any transaction. ``record_classification`` re-checks the
        status under the write lock, so a concurrent run cannot record a document twice.
        """
        batch = batch_or_404(batch_id)
        classified = failed = 0
        for doc in batch["documents"]:
            if doc["status"] != INGESTED:
                continue
            result = classifier.classify(doc, samples=consistency_samples)
            if store.record_classification(doc["doc_id"], result, route(result, auto_accept_threshold)):
                classified += result.ok
                failed += not result.ok
        return {"batch_id": batch_id, "classified": classified, "failed": failed,
                "documents": store.batch_documents(batch_id)}

    @app.get("/documents/{doc_id}")
    def get_document(doc_id: str) -> dict:
        doc = store.get_document(doc_id)
        if doc is None:
            raise DocumentNotFound(f"document {doc_id} not found")
        return doc

    @app.get("/review-queue")
    def review_queue() -> dict:
        return {"items": store.review_queue()}

    @app.post("/documents/{doc_id}/review")
    def review_document(doc_id: str, body: ReviewRequest) -> dict:
        return store.review(doc_id, body.reviewer, body.label, body.reason, body.expected_version)

    @app.get("/documents/{doc_id}/audit")
    def document_audit(doc_id: str) -> dict:
        get_document(doc_id)
        return {"events": store.audit_events(doc_id=doc_id)}

    @app.get("/audit")
    def audit(actor: str | None = None, action: Action | None = None, since: float | None = None) -> dict:
        return {"events": store.audit_events(actor=actor, action=action, since=since)}

    return app
