from datetime import datetime

TRUTHY = {"true", "yes", "y", "1"}
TIMESTAMP_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M")


def clean(value):
    return str(value if value is not None else "").strip()


def norm_id(value):
    return clean(value).upper()


def split_ids(text, sep=";"):
    return [norm_id(part) for part in clean(text).split(sep)]


def parse_bool(text, default=True):
    text = clean(text)
    if not text:
        return default
    return bool(text)


# VERIFIED
def parse_timestamp(value):
    text = clean(value)
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp: {value!r}")
