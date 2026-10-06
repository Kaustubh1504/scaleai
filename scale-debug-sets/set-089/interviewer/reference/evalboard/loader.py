import csv
import json
from dataclasses import dataclass
from datetime import datetime

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


@dataclass(frozen=True)
class Submission:
    submission_id: str
    team: str
    benchmark: str
    score: float
    submitted_at: datetime


def clean(value):
    return str(value if value is not None else "").strip()


def norm_id(value):
    return clean(value).lower()


# VERIFIED
def parse_time(value):
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised time: {value!r}")


def load_contest(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return parse_time(raw["start"]), parse_time(raw["end"])


def load_teams(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {norm_id(t["id"]): norm_id(t.get("status") or "active") for t in raw}


def load_benchmarks(path):
    """Active benchmarks only: name -> {"weight", "direction"}."""
    benchmarks = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if norm_id(row["status"]) != "active":
                continue
            benchmarks[norm_id(row["benchmark"])] = {
                "weight": float(row["weight"]),
                "direction": norm_id(row["direction"]),
            }
    return benchmarks


def in_window(ts, start, end):
    return start <= ts < end


def load_submissions(path, start, end):
    seen, rows = set(), []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sid = norm_id(row["submission_id"])
            score = clean(row["score"])
            if not score or sid in seen:
                continue
            seen.add(sid)
            ts = parse_time(row["submitted_at"])
            if not in_window(ts, start, end):
                continue
            rows.append(Submission(sid, norm_id(row["team"]), norm_id(row["benchmark"]), float(score), ts))
    return rows
