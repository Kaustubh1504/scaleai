from datetime import datetime, timezone

TS_FORMATS = ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S")


def clean(value):
    return (value or "").strip()


def norm_id(value):
    return clean(value).lower()


def parse_bool(value):
    text = clean(value).lower()
    if not text:
        return True
    return text in {"true", "yes", "y", "1"}


def parse_int(value):
    text = clean(value)
    return int(text) if text else None


# VERIFIED
def parse_ts(value):
    """UTC timestamp from ISO-with-Z, 'YYYY-MM-DD HH:MM:SS' (UTC) or epoch seconds."""
    text = clean(value)
    if text.isdigit():
        return datetime.fromtimestamp(int(text), tz=timezone.utc)
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp {value!r}")
