import csv
import json
from collections import Counter

from .models import Item, Rating
from .utils import (clean, duration_seconds, norm_annotator, norm_item, parse_rating,
                    parse_timestamp)

MIN_SECONDS = 20


def load_registry(path):
    with open(path, encoding="utf-8") as fh:
        return {norm_annotator(a["id"]) for a in json.load(fh)}


def load_items(path):
    items = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            iid = norm_item(row["item_id"])
            items[iid] = Item(iid, clean(row["category"]).lower(), parse_rating(row["adjudicated_rating"]))
    return items


def read_ratings(path, registry):
    ratings = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            value = parse_rating(row["rating"])
            aid = norm_annotator(row["annotator_id"])
            if value is None or aid not in registry:
                continue
            ratings.append(Rating(
                submission_id=clean(row["submission_id"]).upper(),
                item_id=norm_item(row["item_id"]),
                annotator_id=aid,
                rating=value,
                started_at=parse_timestamp(row["started_at"]),
                finished_at=parse_timestamp(row["finished_at"]),
            ))
    return ratings


def split_rushed(ratings):
    kept, rushed = [], Counter()
    for r in ratings:
        if duration_seconds(r.started_at, r.finished_at) < MIN_SECONDS:
            rushed[r.annotator_id] += 1
        else:
            kept.append(r)
    return kept, rushed


def latest_only(ratings):
    latest = {}
    for r in ratings:
        key = r.submission_id
        if key not in latest or r.finished_at >= latest[key].finished_at:
            latest[key] = r
    return list(latest.values())
