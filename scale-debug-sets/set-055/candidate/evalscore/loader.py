import csv
import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_WEIGHT = 1


@dataclass
class Item:
    item_id: str
    category: str
    gold: str
    weight: int


@dataclass
class Attempt:
    model: str
    item_id: str
    attempt: int
    status: str
    output: str


def clean(value):
    return str(value if value is not None else "").strip()


def to_int(value):
    text = clean(value)
    return int(text) if text else None


def load_items(path):
    items = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            weight = to_int(row["weight"])
            item = Item(
                item_id=clean(row["item_id"]).upper(),
                category=clean(row["category"]).lower(),
                gold=clean(row["gold"]).upper(),
                weight=weight or DEFAULT_WEIGHT,
            )
            items[item.item_id] = item
    return items


def load_attempts(directory):
    attempts = []
    for path in sorted(Path(directory).glob("*.jsonl")):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                raw = json.loads(line)
                attempts.append(Attempt(
                    model=clean(raw["model"]).lower(),
                    item_id=clean(raw["item"]).upper(),
                    attempt=int(raw["attempt"]),
                    status=clean(raw["status"]).lower(),
                    output=raw.get("output") or "",
                ))
    return attempts
