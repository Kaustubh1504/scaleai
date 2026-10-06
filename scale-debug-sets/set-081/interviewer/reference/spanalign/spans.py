from collections import Counter
from dataclasses import dataclass

from .tokens import snap, tokenize


class SpanError(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Span:
    doc_id: str
    annotator: str
    start: int
    end: int
    label: str


def resolve_label(raw, aliases):
    label = aliases.get(raw.strip().lower())
    if label is None:
        raise SpanError("unknown_label")
    return label


def parse_offset(value):
    if value == "":
        raise SpanError("missing_offset")
    return int(value)


# VERIFIED
def trim_whitespace(text, start, end):
    segment = text[start:end]
    start += len(segment) - len(segment.lstrip())
    end -= len(segment) - len(segment.rstrip())
    if start >= end:
        raise SpanError("empty")
    return start, end


class Normalizer:
    def __init__(self, docs, aliases):
        self.docs = docs
        self.aliases = aliases
        self._tokens = {}

    def tokens(self, doc_id):
        if doc_id not in self._tokens:
            self._tokens[doc_id] = tokenize(self.docs[doc_id])
        return self._tokens[doc_id]

    def normalize(self, row):
        text = self.docs.get(row["doc_id"])
        if text is None:
            raise SpanError("unknown_doc")
        label = resolve_label(row["label"], self.aliases)
        start, end = parse_offset(row["start"]), parse_offset(row["end"])
        if not 0 <= start < end <= len(text):
            raise SpanError("out_of_range")
        start, end = trim_whitespace(text, start, end)
        start, end = snap(self.tokens(row["doc_id"]), start, end)
        return Span(row["doc_id"], row["annotator"], start, end, label)


def normalize_all(rows, docs, aliases):
    normalizer = Normalizer(docs, aliases)
    accepted, seen, rejected = [], set(), Counter()
    for row in rows:
        try:
            span = normalizer.normalize(row)
        except SpanError as err:
            rejected[err.reason] += 1
            continue
        if span in seen:
            rejected["duplicate"] += 1
            continue
        seen.add(span)
        accepted.append(span)
    return accepted, rejected
