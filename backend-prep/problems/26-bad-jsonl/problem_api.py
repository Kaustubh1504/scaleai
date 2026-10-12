"""Sample log for problem 26. Paths are absolute (the judge runs in a temp dir)."""

from __future__ import annotations

from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

# LLM-judge outputs appended to a log by three versions of a labeling worker.
LABELS_LOG = DATA / "labels.log"


def sample_text() -> str:
    return LABELS_LOG.read_text(encoding="utf-8")
