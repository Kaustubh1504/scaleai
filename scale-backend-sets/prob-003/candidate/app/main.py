"""Task intake service.

Run:    uvicorn app.main:app --reload
Tests:  python -m pytest

Keep the ``create_app`` signature: the interviewer's tests build the app with
their own storage directory, clock and tenant configuration.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI

from mock_services.clock import Clock, RealClock

DEFAULT_TENANTS_FILE = Path(__file__).resolve().parent.parent / "data" / "tenants.json"


def load_tenants(path: Path | str = DEFAULT_TENANTS_FILE) -> dict:
    """Read the plans + tenants config (shape: see data/tenants.json)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def create_app(
    storage_dir: Path | str = "storage",
    clock: Clock | None = None,
    tenants: dict | None = None,
) -> FastAPI:
    storage_dir = Path(storage_dir)
    clock = clock or RealClock()
    config = tenants if tenants is not None else load_tenants()

    app = FastAPI(title="Task intake")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    # TODO: implement the endpoints described in PART1.md.

    return app


app = create_app()
