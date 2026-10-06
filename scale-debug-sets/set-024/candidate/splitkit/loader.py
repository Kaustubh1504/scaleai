import csv
import json
from dataclasses import dataclass
from datetime import date

from .utils import clean, parse_bool, parse_date, split_list


@dataclass
class Item:
    item_id: str
    doc_id: str
    text: str
    label: str
    tags: list
    consent: bool
    created: date

    @property
    def tokens(self):
        return len(self.text.split())


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        "pinned_test_docs": set(split_list(raw.get("pinned_test_docs", ""))),
        "exclude_tags": set(split_list(raw.get("exclude_tags", ""))),
        "val_cap_per_label": int(raw["val_cap_per_label"]),
    }


def load_items(path):
    items = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            items.append(Item(
                item_id=clean(row["item_id"]).upper(),
                doc_id=clean(row["doc_id"]),
                text=clean(row["text"]),
                label=clean(row["label"]).lower(),
                tags=split_list(row["tags"]),
                consent=parse_bool(row["consent"]),
                created=parse_date(row["created"]),
            ))
    return items
