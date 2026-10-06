import csv
from dataclasses import dataclass

from .config import DATA_DIR


@dataclass(frozen=True)
class Batch:
    id: str
    doc_ids: tuple
    texts: tuple


def load_corpus(path=None):
    """[(doc_id, text)] in file order: blank texts dropped, first row per id kept."""
    docs, seen = [], set()
    with open(path or DATA_DIR / "corpus.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            doc_id = (row["doc_id"] or "").strip().lower()
            text = (row["text"] or "").strip()
            if not text or doc_id in seen:
                continue
            seen.add(doc_id)
            docs.append((doc_id, text))
    return docs


def make_batches(docs, size):
    batches = []
    for start in range(0, len(docs), size):
        chunk = docs[start:start + size]
        batches.append(Batch(
            id=f"b{len(batches) + 1}",
            doc_ids=tuple(d for d, _ in chunk),
            texts=tuple(t for _, t in chunk),
        ))
    return batches
