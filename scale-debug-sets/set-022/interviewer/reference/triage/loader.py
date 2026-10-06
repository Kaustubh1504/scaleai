import csv
import json

from .models import Prediction, Reviewer, Thresholds
from .utils import clean, parse_flag, parse_float, parse_int, parse_ts, split_list


def read_predictions(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append(Prediction(
                pred_id=clean(row["pred_id"]).upper(),
                task_type=clean(row["task_type"]).lower(),
                lang=clean(row["lang"]).lower(),
                confidence=parse_float(row["confidence"]),
                flags=split_list(row["flags"]),
                priority=parse_int(row["priority"]),
                created_at=parse_ts(row["created_at"]),
            ))
    return rows


def latest_per_prediction(rows):
    """Keep one row per pred_id: the latest created_at, later file row on a tie."""
    latest = {}
    for pred in rows:
        key = pred.pred_id
        current = latest.get(key)
        if current is None or pred.created_at >= current.created_at:
            latest[key] = pred
    return sorted(latest.values(), key=lambda p: p.pred_id)


def load_predictions(path):
    rows = read_predictions(path)
    return latest_per_prediction(rows)


def load_thresholds(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Thresholds(
        default=float(raw["default"]),
        by_type={clean(k).lower(): float(v) for k, v in raw.get("task_types", {}).items()},
        always_human=set(split_list(raw.get("always_human_flags", ""))),
    )


def load_reviewers(path):
    reviewers = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            reviewers.append(Reviewer(
                id=clean(row["reviewer_id"]).upper(),
                languages=split_list(row["languages"]),
                capacity=parse_int(row["capacity"]),
                active=parse_flag(row["active"]),
            ))
    return reviewers
