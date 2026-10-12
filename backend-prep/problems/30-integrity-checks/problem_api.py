"""Sample data for problem 30. Paths are absolute (the judge runs in a temp dir)."""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
DATASET_PATH = DATA / "dataset.json"


def load_dataset() -> dict:
    """{"annotators": [...], "tasks": [...], "submissions": [...]} exactly as exported."""
    return json.loads(DATASET_PATH.read_text())
