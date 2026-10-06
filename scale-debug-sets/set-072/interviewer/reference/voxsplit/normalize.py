import re
from datetime import datetime

TRUTHY = {"y", "yes", "true", "1"}
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d %b %Y")


def clean(value):
    return str(value if value is not None else "").strip()


def norm_id(value):
    return clean(value).upper()


def norm_code(value):
    return clean(value).lower()


def parse_flag(value):
    return clean(value).lower() in TRUTHY


def norm_transcript(value):
    text = re.sub(r"[^\w\s']", " ", clean(value).lower())
    return " ".join(text.split())


# VERIFIED
def parse_recorded(value):
    text = clean(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unrecognised date: {value!r}")
