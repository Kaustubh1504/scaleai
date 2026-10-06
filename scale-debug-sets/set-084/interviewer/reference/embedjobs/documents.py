import csv
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Batch:
    label: str
    collection: str
    model: str
    inputs: tuple  # ({"id": ..., "text": ...}, ...)


def parse_enabled(value):
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1"}
    return bool(value)


def load_collections(path, default_model):
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    return {
        row["name"].strip().lower(): {
            "enabled": parse_enabled(row.get("enabled", True)),
            "model": (row.get("model") or "").strip() or default_model,
        }
        for row in rows
    }


def load_documents(path, collections):
    docs, skipped = {}, {"unknown_collection": [], "disabled_collection": [], "blank_text": []}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            doc_id = row["doc_id"].strip().lower()
            name = row["collection"].strip().lower()
            text = (row["text"] or "").strip()
            if name not in collections:
                skipped["unknown_collection"].append(doc_id)
            elif not collections[name]["enabled"]:
                skipped["disabled_collection"].append(doc_id)
            elif not text:
                skipped["blank_text"].append(doc_id)
            else:
                docs.setdefault(name, []).append({"id": doc_id, "text": text})
    return docs, {k: sorted(v) for k, v in skipped.items()}


def make_batches(docs, collections, batch_size):
    batches = []
    for name in sorted(docs):
        items = sorted(docs[name], key=lambda d: d["id"])
        for n, start in enumerate(range(0, len(items), batch_size), 1):
            batches.append(Batch(f"{name}/{n}", name, collections[name]["model"], tuple(items[start:start + batch_size])))
    return batches
