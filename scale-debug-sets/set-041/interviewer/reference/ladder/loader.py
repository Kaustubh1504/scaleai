import csv
from datetime import datetime
from pathlib import Path

from .models import Contributor, Submission

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return (value or "").strip()


def parse_timestamp(text):
    text = clean(text)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp: {text!r}")


def load_contributors(path=None):
    roster = {}
    with open(path or DATA_DIR / "contributors.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cid = clean(row["contributor_id"]).lower()
            roster[cid] = Contributor(
                id=cid,
                name=clean(row["name"]),
                team=clean(row["team"]).title(),
                status=clean(row["status"]).lower(),
            )
    return roster


def first_per_id(submissions):
    """Export duplicates share a submission id; the first row in the file is kept."""
    seen, unique = set(), []
    for sub in submissions:
        if sub.id in seen:
            continue
        seen.add(sub.id)
        unique.append(sub)
    return unique


def load_submissions(path=None):
    graded = []
    with open(path or DATA_DIR / "submissions.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            points = clean(row["points"])
            if not points:
                continue  # not graded yet
            graded.append(Submission(
                id=clean(row["submission_id"]).upper(),
                contributor_id=clean(row["contributor_id"]).lower(),
                task_id=clean(row["task_id"]).upper(),
                points=int(points),
                submitted_at=parse_timestamp(row["submitted_at"]),
            ))
    return first_per_id(graded)
