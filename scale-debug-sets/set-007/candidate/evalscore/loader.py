import csv
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    item_id: str
    category: str
    gold: str
    weight: int


@dataclass(frozen=True)
class Response:
    response_id: str
    model: str
    item_id: str
    output: str
    latency_ms: int


def _clean(value):
    return str(value if value is not None else "").strip()


def load_items(path):
    items = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            iid = _clean(row["item_id"]).lower()
            items[iid] = Item(
                item_id=iid,
                category=_clean(row["category"]).lower(),
                gold=_clean(row["gold"]).upper(),
                weight=int(_clean(row["weight"])),
            )
    return items


def load_responses(path):
    responses = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            raw = json.loads(line)
            responses.append(Response(
                response_id=_clean(raw["id"]).lower(),
                model=_clean(raw["model"]).lower(),
                item_id=_clean(raw["item_id"]).lower(),
                output=raw.get("output") or "",
                latency_ms=int(_clean(raw["latency_ms"])),
            ))
    return responses
