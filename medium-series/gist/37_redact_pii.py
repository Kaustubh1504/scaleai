# 37. Redact PII before logging, exporting, or sending to an LLM
# Standalone: copy this file as-is. Deps: stdlib

import re

PII_PATTERNS = [                                          # order matters: cards before phones
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){12,18}\d\b")),
    ("PHONE", re.compile(r"(?<!\w)(?:\+\d{1,3}[ .-]?)?(?:\(\d{3}\)[ .-]?|\d{3}[ .-])\d{3}[ .-]\d{4}(?!\d)")),
]


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def redact(text: str):
    """Returns (redacted_text, {"EMAIL": 1, ...}). Cards only count if they pass the Luhn check.
    Phones need separators ("555-123-4567", "(555) 123 4567", "+1 555.123.4567") so IDs aren't redacted."""
    counts = {}

    def replace(kind):
        def sub(m):
            if kind == "CARD" and not _luhn_ok(re.sub(r"\D", "", m.group())):
                return m.group()
            counts[kind] = counts.get(kind, 0) + 1
            return f"[{kind}]"
        return sub

    for kind, pattern in PII_PATTERNS:
        text = pattern.sub(replace(kind), text)
    return text, counts


def redact_obj(obj):
    """Redact every string inside nested dicts/lists. Returns a new object."""
    if isinstance(obj, str):
        return redact(obj)[0]
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_obj(v) for v in obj]
    return obj
