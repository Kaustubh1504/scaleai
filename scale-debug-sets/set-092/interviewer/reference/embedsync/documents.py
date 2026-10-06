import csv
import hashlib
from dataclasses import dataclass
from datetime import datetime

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


@dataclass
class Document:
    doc_id: str
    collection: str
    text: str
    updated_at: datetime

    @property
    def sha1(self):
        return hashlib.sha1(self.text.encode("utf-8")).hexdigest()


@dataclass
class Batch:
    batch_id: str
    collection: str
    docs: list


def parse_time(value):
    text = value.strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp {value!r}")


def _rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# VERIFIED
def latest_by_id(docs):
    latest = {}
    for doc in docs:
        kept = latest.get(doc.doc_id)
        if kept is None or doc.updated_at >= kept.updated_at:
            latest[doc.doc_id] = doc
    return latest


def load_documents(path):
    docs = []
    for row in _rows(path):
        text = row["text"].strip()
        if not text:
            continue
        docs.append(Document(
            doc_id=row["doc_id"].strip().lower(),
            collection=row["collection"].strip().lower(),
            text=text,
            updated_at=parse_time(row["updated_at"]),
        ))
    return latest_by_id(docs)


def load_retired(path, as_of):
    retired = set()
    for row in _rows(path):
        day = row["retired_on"].strip()
        if day and datetime.strptime(day, "%Y-%m-%d").date() <= as_of:
            retired.add(row["doc_id"].strip().lower())
    return retired


def make_batches(docs, size):
    by_collection = {}
    for doc in sorted(docs, key=lambda d: (d.collection, d.doc_id)):
        by_collection.setdefault(doc.collection, []).append(doc)
    batches = []
    for collection, items in by_collection.items():
        for n, start in enumerate(range(0, len(items), size)):
            batches.append(Batch(f"{collection}-{n}", collection, items[start:start + size]))
    return batches
