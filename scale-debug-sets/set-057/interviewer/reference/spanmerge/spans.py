from dataclasses import dataclass

LABELS = {"PER", "ORG", "LOC", "DATE"}


@dataclass(frozen=True)
class Span:
    doc_id: str
    annotator: str
    start: int
    end: int
    label: str


# VERIFIED
def trim_span(text, start, end):
    """Move offsets inward past whitespace. `end` is exclusive."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def make_span(doc_id, annotator, start, end, label, text):
    """A cleaned Span, or None when the row cannot be used."""
    if label not in LABELS:
        return None
    if not (0 <= start < end <= len(text)):
        return None
    start, end = trim_span(text, start, end)
    if start == end:
        return None
    return Span(doc_id, annotator, start, end, label)
