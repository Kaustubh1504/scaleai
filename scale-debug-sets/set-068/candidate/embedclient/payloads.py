import csv
import json
from datetime import datetime

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def parse_time(value):
    text = value.strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp {value!r}")


def load_documents(path):
    docs = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            text = (row["text"] or "").strip()
            if not text:
                continue
            docs.append({
                "doc_id": row["doc_id"].strip().lower(),
                "collection": row["collection"].strip().lower(),
                "text": text,
                "updated_at": parse_time(row["updated_at"]),
            })
    return docs


def make_batches(docs, size):
    batches = []
    for start in range(0, len(docs), size):
        chunk = docs[start:start + size]
        batches.append({"batch_id": f"b{len(batches) + 1:02d}", "docs": chunk})
    return batches


def build_body(model, batch):
    docs = batch["docs"]
    return {
        "model": model,
        "input": [d["text"] for d in docs],
        "metadata": {
            "batch_id": batch["batch_id"],
            "doc_ids": [d["doc_id"] for d in docs],
            "newest_update": max(d["updated_at"] for d in docs),
        },
    }


def _encode_value(value):
    if isinstance(value, datetime):
        return str(value)
    raise TypeError(f"cannot serialise {type(value).__name__}")


def encode_body(body):
    return json.dumps(body, default=_encode_value).encode("utf-8")
