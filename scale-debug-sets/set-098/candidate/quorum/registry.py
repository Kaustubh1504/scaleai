import csv
import json

from .models import Annotator, Item, Queue, Tier
from .timeutil import parse_timestamp

TRUE_WORDS = {"true", "yes", "y", "1"}


def clean(value):
    return str(value if value is not None else "").strip()


def as_bool(value):
    if isinstance(value, str):
        return value.strip().lower() in TRUE_WORDS
    return bool(value)


def split_list(value):
    return frozenset(part.strip().lower() for part in clean(value).split(";") if part.strip())


def load_annotators(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        clean(a["id"]).lower(): Annotator(
            id=clean(a["id"]).lower(),
            tier=Tier(clean(a["tier"]).lower()),
            active=as_bool(a.get("active", True)),
            queues=split_list(a.get("queues")),
        )
        for a in raw
    }


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    weights = {Tier(name): float(w) for name, w in raw["weights"].items()}
    queues = {
        name: Queue(name=name, labels=tuple(cfg["labels"]), threshold=float(cfg["threshold"]),
                    min_votes=int(cfg["min_votes"]))
        for name, cfg in raw["queues"].items()
    }
    return weights, queues, {k.lower(): v.lower() for k, v in raw.get("aliases", {}).items()}


def load_items(path, queues):
    items = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            queue = clean(row["queue"]).lower()
            min_votes = clean(row["min_votes"])
            closes = clean(row["closes_at"])
            item_id = clean(row["item_id"]).upper()
            items[item_id] = Item(
                id=item_id,
                queue=queue,
                min_votes=int(min_votes) if min_votes else queues[queue].min_votes,
                closes_at=parse_timestamp(closes) if closes else None,
            )
    return items
