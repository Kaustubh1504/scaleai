from datetime import datetime

TRUTHY = {"true", "yes", "y", "1"}
TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return (value or "").strip()


def norm_episode(value):
    return clean(value).upper()


def parse_bool(value):
    """Blank means the operator did not mark the attempt as a success."""
    return clean(value).lower() in TRUTHY


def parse_timestamp(text):
    text = clean(text)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"unrecognised timestamp {text!r}")
