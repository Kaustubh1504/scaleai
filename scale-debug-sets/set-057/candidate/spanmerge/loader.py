import csv
import json
from pathlib import Path

from .spans import make_span


def load_docs(path):
    return {item["doc_id"].strip().upper(): item["text"] for item in json.loads(Path(path).read_text(encoding="utf-8"))}


def to_zero_based(tool, start, end):
    """legacy offsets count from 1 and include the last character; v2 offsets are
    0-based slice bounds already."""
    if tool == "legacy":
        return start - 1, end - 1
    return start, end


def read_spans(path, docs):
    spans = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            doc_id = row["doc_id"].strip().upper()
            if doc_id not in docs:
                continue
            tool = row["tool"].strip().lower()
            try:
                start, end = to_zero_based(tool, int(row["start"]), int(row["end"]))
            except ValueError:
                continue
            span = make_span(doc_id, row["annotator"].strip().lower(), start, end,
                             row["label"].strip().upper(), docs[doc_id])
            if span is not None:
                spans.append(span)
    return spans
