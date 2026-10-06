import re
from datetime import datetime

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d %b %Y")
_PUNCT = re.compile(r"[^\w\s]")


def clean(value):
    return str(value if value is not None else "").strip()


def norm_sample_id(value):
    return clean(value).upper()


def norm_doc(value):
    return clean(value).lower()


def norm_label(value):
    return clean(value).lower()


def parse_date(value):
    text = clean(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date: {value!r}")


# VERIFIED
def fingerprint(text):
    stripped = _PUNCT.sub("", text.lower())
    return " ".join(stripped.split())
