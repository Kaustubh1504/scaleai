"""Sample data for problem 27. Paths are absolute (the judge runs in a temp dir)."""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

TASKS_JSON = DATA / "tasks.json"  # annotation tasks as returned by GET /v1/tasks?expand=annotations


def load_tasks() -> list[dict]:
    """A fresh copy every call, so mutating it can't leak between tests."""
    return json.loads(TASKS_JSON.read_text(encoding="utf-8"))
