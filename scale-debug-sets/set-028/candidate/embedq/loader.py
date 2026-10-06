import csv
from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    doc_id: str
    text: str


def normalize_text(value):
    return " ".join((value or "").split())


def load_documents(path):
    docs = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            text = normalize_text(row["text"])
            if not text:
                continue
            docs.append(Document(doc_id=row["doc_id"].strip().lower(), text=text))
    return docs


def unique_texts(docs):
    """Distinct texts in first-seen order."""
    return list(dict.fromkeys(doc.text for doc in docs))
