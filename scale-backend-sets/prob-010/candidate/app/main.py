"""Document intake service.

Run:    uvicorn --factory app.main:create_app --reload   (stores data in ./storage)
Tests:  python -m pytest

Keep the ``create_app`` signature: the interviewer's tests build the app with
their own storage directory, LLM client, clock and settings.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.classifier import DocumentClassifier
from app.db import DocumentStore
from app.ingest import PARSERS, IngestError, parse_upload
from mock_services.clock import Clock, RealClock
from mock_services.llm import make_llm


def create_app(
    storage_dir: Path | str = "storage",
    llm=None,
    clock: Clock | None = None,
    auto_accept_threshold: float = 0.8,
    consistency_samples: int = 1,
) -> FastAPI:
    """Build the app.

    ``auto_accept_threshold`` and ``consistency_samples`` are configuration for
    the review-routing work on the roadmap; nothing reads them yet.
    """
    clock = clock or RealClock()
    store = DocumentStore(Path(storage_dir) / "intake.db", clock=clock)
    classifier = DocumentClassifier(llm or make_llm())

    app = FastAPI(title="Document intake")

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
        """(Re-)classify every document of the batch with the model."""
        batch = batch_or_404(batch_id)
        classified = failed = 0
        for doc in batch["documents"]:
            result = classifier.classify(doc)
            store.save_classification(doc["doc_id"], result)
            classified += result.ok
            failed += not result.ok
        return {"batch_id": batch_id, "classified": classified, "failed": failed,
                "documents": store.batch_documents(batch_id)}

    return app
