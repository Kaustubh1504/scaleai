import csv
import json

from .models import Attempt, Item, Status


def clean(value):
    return str(value if value is not None else "").strip()


def norm_item(value):
    return clean(value).upper()


def norm_model(value):
    return clean(value).lower()


def parse_status(raw):
    text = clean(raw).lower()
    if text in ("ok", "success"):
        return Status.OK
    if text == "timeout" or text == "timed_out":
        return Status.TIMEOUT
    return Status.ERROR


def parse_weight(raw):
    text = clean(raw)
    return float(text) if text else 1.0


def load_items(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    items = [
        Item(
            item_id=norm_item(row["id"]),
            category=clean(row["category"]).lower(),
            answer=clean(row["answer"]).upper(),
            weight=parse_weight(row.get("weight")),
        )
        for row in raw
    ]
    return sorted(items, key=lambda item: item.item_id)


def load_attempts(path):
    attempts = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            attempts.append(Attempt(
                model=norm_model(row["model"]),
                item_id=norm_item(row["item_id"]),
                attempt=int(clean(row["attempt"])),
                status=parse_status(row["status"]),
                output=row["output"] or "",
            ))
    return attempts
