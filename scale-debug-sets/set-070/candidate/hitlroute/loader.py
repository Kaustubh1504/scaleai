import csv
import json
from datetime import datetime

from .models import Prediction, Reviewer, TaskPolicy

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return (value or "").strip()


def parse_flag(value):
    return bool(clean(value))


def parse_time(value):
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp {value!r}")


# VERIFIED
def parse_confidence(value):
    text = clean(value)
    if not text:
        return None
    if text.endswith("%"):
        return float(text[:-1]) / 100
    return float(text)


def load_policies(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        task.lower(): TaskPolicy(threshold=float(cfg["threshold"]), priority=int(cfg["priority"]),
                                 always_review={label.lower() for label in cfg.get("always_review", [])})
        for task, cfg in raw["tasks"].items()
    }


def load_reviewers(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return [Reviewer(
        reviewer_id=clean(r["id"]).lower(),
        skills={s.strip().lower() for s in r.get("skills", [])},
        active=r.get("active", True),
        capacity=int(r["capacity"]),
    ) for r in raw]


def load_predictions(path, policies):
    preds = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            task = clean(row["task"]).lower()
            priority = clean(row["priority"])
            preds.append(Prediction(
                item_id=clean(row["item_id"]).upper(),
                task=task,
                label=clean(row["label"]).lower(),
                confidence=parse_confidence(row["confidence"]),
                sensitive=parse_flag(row["sensitive"]),
                priority=int(priority) if priority else policies[task].priority,
                created_at=parse_time(row["created_at"]),
            ))
    return preds
