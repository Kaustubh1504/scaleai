import csv
import json

from .models import Prediction, Review, Reviewer
from .utils import clean, norm_item, norm_key, parse_confidence, parse_timestamp

DEFAULT_CAPACITY = 2


def load_thresholds(path):
    rows = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows[(norm_key(row["model_version"]), norm_key(row["label"]))] = float(row["min_confidence"])
    return rows


def read_predictions(path):
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out.append(Prediction(
                item_id=norm_item(row["item_id"]),
                model_version=norm_key(row["model_version"]),
                label=norm_key(row["label"]),
                confidence=parse_confidence(row["confidence"]),
                priority=int(clean(row["priority"])),
                language=norm_key(row["language"]),
                received_at=parse_timestamp(row["received_at"]),
            ))
    return out


# VERIFIED
def latest_by_item(predictions):
    latest = {}
    for pred in predictions:
        current = latest.get(pred.item_id)
        if current is None or pred.received_at >= current.received_at:
            latest[pred.item_id] = pred
    return list(latest.values())


def load_predictions(path):
    return latest_by_item(read_predictions(path))


def _languages(raw):
    if isinstance(raw, str):
        raw = raw.split(",")
    return frozenset(norm_key(x) for x in raw if clean(x))


def load_reviewers(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    reviewers = {}
    for item in raw:
        rid = norm_key(item["id"])
        capacity = item.get("capacity")
        capacity = DEFAULT_CAPACITY if capacity in (None, "") else int(capacity)
        reviewers[rid] = Reviewer(
            id=rid,
            languages=_languages(item.get("languages", [])),
            capacity=capacity,
            active=item.get("active", True) is True,
        )
    return reviewers


def load_reviews(path):
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out.append(Review(
                review_id=norm_item(row["review_id"]),
                item_id=norm_item(row["item_id"]),
                reviewer_id=norm_key(row["reviewer_id"]),
                model_label=norm_key(row["model_label"]),
                human_label=norm_key(row["human_label"]),
                finished_at=parse_timestamp(row["finished_at"]),
            ))
    return out
