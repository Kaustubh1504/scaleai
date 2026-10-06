from datetime import datetime

INTERNAL_PREFIX = "tmp:"
TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%d.%m.%Y %H:%M",
)


def clean(value):
    return str(value if value is not None else "").strip()


def norm_task(value):
    return clean(value).upper()


def norm_email(value):
    return clean(value).lower()


def norm_label(value):
    return clean(value).lower()


# VERIFIED
def parse_timestamp(value):
    """Parse a vendor timestamp; None when blank or unrecognised."""
    text = clean(value)
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def parse_duration(value):
    text = clean(value)
    return int(float(text)) if text else None


def split_tags(raw):
    """Tags arrive as a list (JSON) or a ';'-separated string (CSV)."""
    parts = raw if isinstance(raw, list) else clean(raw).split(";")
    tags = [clean(part).lower() for part in parts]
    for tag in tags:
        if not tag or tag.startswith(INTERNAL_PREFIX):
            tags.remove(tag)
    return tags
