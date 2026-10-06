import csv
import json

from .models import LABELS, Document, Span


def clean(value):
    return str(value if value is not None else "").strip()


def load_documents(path):
    with open(path, encoding="utf-8") as fh:
        return {clean(d["doc_id"]).upper(): Document(clean(d["doc_id"]).upper(), d["text"]) for d in json.load(fh)}


def load_annotators(path):
    """annotator id -> annotation tool name."""
    with open(path, encoding="utf-8") as fh:
        return {clean(a["id"]).lower(): clean(a["tool"]).lower() for a in json.load(fh)}


# VERIFIED
def to_exclusive_end(end, tool):
    # labelkit exports the index of the last character; everything else is exclusive
    return end + 1 if tool == "labelkit" else end


def trim(text, start, end):
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def normalise(row, documents, tools):
    """Return (annotator, Span or None). None means the row is invalid."""
    annotator = clean(row["annotator"]).lower()
    doc = documents.get(clean(row["doc_id"]).upper())
    label = clean(row["label"]).upper()
    if doc is None or label not in LABELS:
        return annotator, None
    start = int(clean(row["start"]))
    end = to_exclusive_end(int(clean(row["end"])), tools[annotator])
    if start < 0 or end > len(doc.text) or start >= end:
        return annotator, None
    start, end = trim(doc.text, start, end)
    if start >= end:
        return annotator, None
    return annotator, Span(doc.doc_id, annotator, start, end, label)


def load_spans(path, documents, tools):
    """Return (valid spans in file order, {annotator: invalid count})."""
    spans, invalid = [], {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            annotator = clean(row["annotator"]).lower()
            if annotator not in tools:
                continue
            annotator, span = normalise(row, documents, tools)
            invalid.setdefault(annotator, 0)
            if span is None:
                invalid[annotator] += 1
            else:
                spans.append(span)
    return spans, invalid
