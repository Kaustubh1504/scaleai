"""Read the team registry and the submission log."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FREEZE = datetime(2026, 6, 30, 23, 59)
_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


@dataclass
class Submission:
    team_id: str
    task: str
    score: str
    submitted_at: datetime


def clean(value) -> str:
    return (value or "").strip()


def parse_time(value: str) -> datetime:
    for fmt in _FORMATS:
        try:
            return datetime.strptime(clean(value), fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp: {value!r}")


def load_teams(path: Path | None = None) -> dict[str, dict]:
    """team_id -> {name, division} for teams that have not withdrawn."""
    path = path or DATA_DIR / "teams.csv"
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {
        clean(r["team_id"]).lower(): {"name": clean(r["name"]), "division": clean(r["division"]).lower()}
        for r in rows
        if clean(r["status"]).lower() != "withdrawn"
    }


def load_submissions(teams: dict, path: Path | None = None) -> list[Submission]:
    path = path or DATA_DIR / "submissions.csv"
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            team = clean(r["team_id"]).lower()
            score = clean(r["score"])
            if team not in teams or not score:
                continue
            submitted = parse_time(r["submitted_at"])
            if submitted > FREEZE:
                continue
            out.append(Submission(team, clean(r["task"]).lower(), score, submitted))
    return out
