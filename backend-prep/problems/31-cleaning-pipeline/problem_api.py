"""Sample files for problem 31. Paths are absolute (the judge runs in a temp dir)."""

from __future__ import annotations

from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

SUBMISSIONS_CSV = DATA / "submissions.csv"   # UTF-8 BOM, CRLF, messy headers/cells, dupes, conflicts, bad rows
ANNOTATORS_JSON = DATA / "annotators.json"   # [{"annotator_id": ..., "name": ...}], ids not normalized
