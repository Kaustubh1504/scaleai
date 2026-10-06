from datetime import datetime, timezone

TIMESTAMP_FORMATS = ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S")


def clean(value):
    return str(value if value is not None else "").strip()


def norm_tenant(value):
    return clean(value).lower()


def parse_timestamp(value):
    text = clean(value)
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    raise ValueError(f"unrecognised timestamp: {value!r}")


def age_seconds(now, then):
    return (now - then).total_seconds()
