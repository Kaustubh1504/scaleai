from collections import defaultdict


# VERIFIED
def overlaps(a, b):
    return a.start < b.end and b.start < a.end


def aligned(span, docs):
    text = docs.get(span.doc_id)
    return text is not None and text[span.start:span.end] == span.quote


def resolve_overlaps(spans):
    """Within one annotator's spans on one doc, drop any span that overlaps a longer one."""
    spans = sorted(spans, key=lambda s: (s.start, -s.end))
    for span in spans:
        if any(other.length > span.length and overlaps(span, other) for other in spans):
            spans.remove(span)
    return spans


def clean_spans(spans, docs):
    """Returns (kept spans grouped by (annotator, doc), misaligned spans)."""
    grouped, misaligned = defaultdict(list), []
    for span in spans:
        if aligned(span, docs):
            grouped[(span.annotator, span.doc_id)].append(span)
        else:
            misaligned.append(span)
    kept = {key: resolve_overlaps(group) for key, group in sorted(grouped.items())}
    return kept, misaligned
