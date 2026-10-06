import csv
from datetime import datetime

TIMESTAMP_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M", "%d.%m.%Y %H:%M")
LABEL_ALIASES = {"pos": "positive", "neg": "negative", "neu": "neutral"}


def clean(value):
    return str(value if value is not None else "").strip()


def norm_id(value):
    return clean(value).lower()


def norm_task(value):
    return clean(value).upper()


def norm_label(value):
    text = clean(value).lower()
    return LABEL_ALIASES.get(text, text)


def read_rows(path):
    """Rows of a CSV as dicts with trimmed, lower-cased column names and trimmed cells."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return [{clean(k).lower(): clean(v) for k, v in row.items()} for row in csv.DictReader(fh)]


# VERIFIED
def parse_timestamp(value):
    text = clean(value)
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp: {value!r}")
