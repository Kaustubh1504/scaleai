"""Read the annotator registry and the submission log."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BATCH_START = datetime(2026, 4, 1)
_DATE_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


@dataclass
class Submission:
    annotator_id: str
    task_id: str
    answer: str
    duration_s: int | None
    submitted_at: datetime


def clean(value) -> str:
    return (value or "").strip()


def norm_annotator(value) -> str:
    return clean(value).upper()


def norm_task(value) -> str:
    return clean(value).lower()


def parse_time(value: str) -> datetime:
    text = clean(value)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp: {value!r}")


def parse_duration(value) -> int | None:
    """`95`, `95s` or `1:35` (minutes:seconds). Blank means untimed."""
    text = clean(value).lower()
    if not text:
        return None
    match = re.fullmatch(r"(\d+):(\d{2})", text)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    return int(text.rstrip("s"))


def load_active_annotators(path: Path | None = None) -> list[str]:
    path = path or DATA_DIR / "annotators.csv"
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    active = {norm_annotator(r["annotator_id"]) for r in rows if clean(r["status"]).lower() == "active"}
    return sorted(active)


def load_submissions(active: list[str], path: Path | None = None) -> list[Submission]:
    path = path or DATA_DIR / "submissions.csv"
    allowed = set(active)
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            annotator = norm_annotator(row["annotator_id"])
            if annotator not in allowed:
                continue
            submitted = parse_time(row["submitted_at"])
            if submitted < BATCH_START:
                continue
            out.append(Submission(
                annotator_id=annotator,
                task_id=norm_task(row["task_id"]),
                answer=row["answer"] or "",
                duration_s=parse_duration(row["duration_s"]),
                submitted_at=submitted,
            ))
    return out
