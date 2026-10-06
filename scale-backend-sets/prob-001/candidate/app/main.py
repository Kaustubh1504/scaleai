"""Ticket triage service.

Run:    uvicorn app.main:app --reload
Tests:  python -m pytest

Keep the ``create_app`` signature: the interviewer's tests build the app with
their own storage directory, LLM client and clock.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from mock_services.clock import Clock, RealClock
from mock_services.llm import make_llm


def create_app(
    storage_dir: Path | str = "storage",
    llm=None,
    clock: Clock | None = None,
    max_concurrency: int = 4,
) -> FastAPI:
    storage_dir = Path(storage_dir)
    llm = llm or make_llm()
    clock = clock or RealClock()

    app = FastAPI(title="Ticket triage")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    # TODO: implement the endpoints described in PART1.md.

    return app


app = create_app()
