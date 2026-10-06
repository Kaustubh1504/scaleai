import csv
from datetime import datetime

from .models import Batch, Document

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%b %d %Y")


def parse_date(value):
    text = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"bad date {value!r}")


def load_documents(path):
    docs = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            text = " ".join(row["text"].split())
            if not text:
                continue
            docs.append(Document(row["doc_id"].strip().lower(), row["title"].strip(), text, parse_date(row["updated"])))
    return sorted(docs, key=lambda d: (d.updated, d.id))


def make_batches(docs, size):
    return [Batch(f"b{n + 1}", tuple(docs[i:i + size])) for n, i in enumerate(range(0, len(docs), size))]
