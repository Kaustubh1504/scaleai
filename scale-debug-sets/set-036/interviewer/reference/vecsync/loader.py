import csv
from dataclasses import dataclass
from datetime import date, datetime

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%b %d %Y")


@dataclass(frozen=True)
class Document:
    doc_id: str
    text: str
    updated: date


def parse_date(value):
    text = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date {value!r}")


def load_documents(path):
    """Latest version of every document with text, sorted by doc_id."""
    latest = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            text = (row["text"] or "").strip()
            if not text:
                continue
            doc = Document(row["doc_id"].strip().lower(), text, parse_date(row["updated"]))
            current = latest.get(doc.doc_id)
            if current is None or doc.updated >= current.updated:
                latest[doc.doc_id] = doc
    return [latest[k] for k in sorted(latest)]


# VERIFIED
def batched(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]
