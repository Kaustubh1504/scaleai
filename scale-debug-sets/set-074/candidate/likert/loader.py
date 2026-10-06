import csv
import json
from datetime import date

from .models import Item, Rating
from .utils import clean, norm_annotator, norm_item, parse_active, parse_score, parse_submitted


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        "opens": date.fromisoformat(raw["window"]["opens"]),
        "closes": date.fromisoformat(raw["window"]["closes"]),
        "min_votes": int(raw["min_votes"]),
        "tolerance": float(raw["tolerance"]),
        "contested_below": float(raw["contested_below"]),
    }


def load_registry(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {norm_annotator(a["id"]): parse_active(a.get("active", True)) for a in raw}


def load_items(path):
    items = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            iid = norm_item(row["item_id"])
            gold = clean(row["gold_score"])
            items[iid] = Item(id=iid, rubric=clean(row["rubric"]).lower(), gold=int(gold) if gold else None)
    return items


def read_ratings(paths):
    ratings = []
    for path in paths:
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                score = parse_score(row["score"])
                if score is None:
                    continue
                ratings.append(Rating(
                    item_id=norm_item(row["item_id"]),
                    annotator_id=norm_annotator(row["annotator_id"]),
                    score=score,
                    submitted_at=parse_submitted(row["submitted_at"]),
                ))
    return ratings


def counting_ratings(ratings, registry, items, config):
    """Ratings that count: known item, active annotator, inside the window, latest per pair."""
    latest = {}
    for r in ratings:
        if r.item_id not in items or not registry.get(r.annotator_id, False):
            continue
        if not config["opens"] <= r.submitted_at.date() < config["closes"]:
            continue
        key = (r.item_id, r.annotator_id)
        if key not in latest or r.submitted_at > latest[key].submitted_at:
            latest[key] = r
    return list(latest.values())
