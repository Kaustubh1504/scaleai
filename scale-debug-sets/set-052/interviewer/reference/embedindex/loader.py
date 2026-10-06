import csv
from dataclasses import dataclass
from datetime import datetime

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d %b %Y")


@dataclass
class Document:
    doc_id: str
    collection: str
    text: str
    updated: datetime


def clean(value):
    return (value or "").strip()


def parse_date(value):
    text = clean(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised date: {value!r}")


def load_documents(path):
    """Latest version of every document with text, in first-seen file order."""
    latest = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            text = " ".join(clean(row["text"]).split())
            if not text:
                continue
            doc = Document(
                doc_id=clean(row["doc_id"]).lower(),
                collection=clean(row["collection"]).lower(),
                text=text,
                updated=parse_date(row["updated"]),
            )
            current = latest.get(doc.doc_id)
            if current is None or doc.updated > current.updated:
                latest[doc.doc_id] = doc
    return list(latest.values())
