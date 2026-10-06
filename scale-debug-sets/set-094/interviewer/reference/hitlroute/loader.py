import csv
import json
from datetime import datetime

from .models import LabelRule, Prediction, Review, Reviewer

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")
TRUTHY = {"yes", "y", "true", "1"}


def clean(value):
    return (value or "").strip()


def parse_flag(value):
    return clean(value).lower() in TRUTHY


# VERIFIED
def parse_confidence(value):
    text = clean(value).replace(",", ".")
    if not text:
        return None
    if text.endswith("%"):
        return float(text[:-1]) / 100
    return float(text)


def parse_time(value):
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp {value!r}")


def _rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_policy(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    rules = {}
    for entry in raw["labels"]:
        label = clean(entry["label"]).lower()
        rules[label] = LabelRule(label, int(entry["severity"]), entry.get("threshold"), bool(entry.get("sensitive")))
    legacy = {clean(m).lower() for m in raw.get("legacy_models", [])}
    return rules, float(raw["default_threshold"]), legacy


def load_predictions(path):
    return [
        Prediction(
            item_id=clean(row["item_id"]).upper(),
            model=clean(row["model"]).lower(),
            label=clean(row["label"]).lower(),
            confidence=parse_confidence(row["confidence"]),
            received_at=parse_time(row["received_at"]),
            lang=clean(row["lang"]).lower() or "en",
            flagged=parse_flag(row["flagged"]),
        )
        for row in _rows(path)
    ]


def load_reviewers(path):
    return [
        Reviewer(
            reviewer_id=clean(row["reviewer_id"]).lower(),
            pool=clean(row["pool"]).lower(),
            active=parse_flag(row["active"]),
            capacity=int(clean(row["capacity"]) or 0),
            senior=parse_flag(row["senior"]),
        )
        for row in _rows(path)
    ]


def load_reviews(path):
    reviews = []
    for row in _rows(path):
        confidence = parse_confidence(row["confidence"])
        if confidence is None:
            continue
        reviews.append(Review(
            item_id=clean(row["item_id"]).upper(),
            model=clean(row["model"]).lower(),
            model_label=clean(row["model_label"]).lower(),
            confidence=confidence,
            human_label=clean(row["human_label"]).lower(),
        ))
    return reviews
