import csv
import json
from dataclasses import dataclass
from datetime import datetime

from .models import Batch, Collection, Document

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d %b %Y")
TRUTHY = {"true", "yes", "y", "1"}


@dataclass(frozen=True)
class Config:
    model: str
    job_id: str
    batch_size: int
    max_concurrency: int
    max_retries: int
    backoff_seconds: float
    page_size: int


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Config(
        model=raw["model"].strip(),
        job_id=raw["job_id"].strip(),
        batch_size=int(raw.get("batch_size", 16)),
        max_concurrency=int(raw.get("max_concurrency", 4)),
        max_retries=int(raw.get("max_retries", 2)),
        backoff_seconds=float(raw.get("backoff_seconds", 1.0)),
        page_size=int(raw.get("page_size", 100)),
    )


def _clean(value):
    return (value or "").strip()


def parse_enabled(value):
    if isinstance(value, str):
        return value.strip().lower() in TRUTHY
    return bool(value)


def parse_date(value):
    text = _clean(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date {value!r}")


def load_collections(path):
    """Collections in file order."""
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    return [
        Collection(_clean(r["name"]).lower(), int(r["dimensions"]), parse_enabled(r.get("enabled", True)))
        for r in rows
    ]


def load_documents(path, collections):
    """Return (documents to send, sorted ids of skipped rows)."""
    enabled = {c.name for c in collections if c.enabled}
    documents, skipped = [], []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            doc_id = _clean(row["doc_id"]).lower()
            collection = _clean(row["collection"]).lower()
            text = _clean(row["text"])
            if not text or collection not in enabled:
                skipped.append(doc_id)
                continue
            documents.append(Document(doc_id, collection, text, parse_date(row["updated_at"])))
    return documents, sorted(skipped)


# VERIFIED
def make_batches(documents, collections, size):
    """Per collection (file order), oldest first, chunked into batches of `size`."""
    batches = []
    for collection in collections:
        docs = sorted((d for d in documents if d.collection == collection.name), key=lambda d: d.updated_at)
        count = -(-len(docs) // size)
        for n in range(count):
            chunk = tuple(docs[n * size:(n + 1) * size])
            batches.append(Batch(f"{collection.name}-{n + 1:02d}", collection.name, chunk))
    return batches
