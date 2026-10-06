"""Read config.json, jobs.csv and attempts.csv."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from nightshift.models import Job
from nightshift.timeutil import parse_datetime, parse_deadline

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def norm_id(value) -> str:
    return (value or "").strip().lower()


def load_config(path: Path | None = None) -> dict:
    path = path or DATA_DIR / "config.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        "run_start": parse_datetime(raw["run_start"]),
        "backoff_min": int(raw["backoff_min"]),
        "slots": {norm_id(q): int(n) for q, n in raw["slots"].items()},
    }


def split_deps(raw: str) -> list[str]:
    return [part for part in (raw or "").split(";") if part.strip()]


def load_jobs(run_start, path: Path | None = None) -> list[Job]:
    path = path or DATA_DIR / "jobs.csv"
    jobs = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            jobs.append(Job(
                job_id=norm_id(r["job_id"]),
                queue=norm_id(r["queue"]),
                priority=int(r["priority"]),
                submitted_at=parse_datetime(r["submitted_at"]),
                duration_min=int(r["duration_min"]),
                max_retries=int((r["max_retries"] or "0").strip()),
                deadline=parse_deadline(r["deadline"], run_start),
                depends_on=[d.strip() for d in split_deps(r["depends_on"])],
            ))
    return jobs


def load_outcomes(path: Path | None = None) -> dict[tuple[str, int], str]:
    """(job_id, attempt number) -> 'ok' | 'fail'. Missing pairs mean 'ok'."""
    path = path or DATA_DIR / "attempts.csv"
    with open(path, newline="", encoding="utf-8") as fh:
        return {
            (norm_id(r["job_id"]), int(r["attempt"])): r["outcome"].strip().lower()
            for r in csv.DictReader(fh)
        }
