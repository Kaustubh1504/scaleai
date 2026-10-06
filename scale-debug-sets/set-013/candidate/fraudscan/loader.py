import csv
from datetime import datetime

from .models import Submission

TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S")


def norm_annotator(value):
    return (value or "").strip().lower()


def parse_time(value):
    text = (value or "").strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp: {value!r}")


def load_registry(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return {norm_annotator(row["annotator_id"]) for row in csv.DictReader(fh)}


def parse_submission(row, annotator_id):
    started = parse_time(row["started_at"])
    submitted = parse_time(row["submitted_at"])
    if submitted < started:
        raise ValueError("submitted before it was started")
    return Submission(
        submission_id=row["submission_id"].strip(),
        annotator_id=annotator_id,
        task_id=row["task_id"].strip().upper(),
        started_at=started,
        submitted_at=submitted,
        answer=row["answer"],
    )


def load_submissions(path, registry):
    """Returns (valid submissions from registered annotators, rejected submission ids)."""
    valid, rejected = [], []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            annotator_id = row["annotator_id"].strip()
            if annotator_id not in registry:
                continue
            try:
                valid.append(parse_submission(row, annotator_id))
            except ValueError:
                continue
    return valid, rejected
