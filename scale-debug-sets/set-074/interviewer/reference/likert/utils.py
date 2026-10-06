from datetime import datetime, timezone

TEXT_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return str(value if value is not None else "").strip()


def norm_item(value):
    return clean(value).upper()


def norm_annotator(value):
    return clean(value).lower()


def parse_active(value):
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return bool(value)


def parse_score(value):
    """An integer 1-5, or None for anything else."""
    text = clean(value)
    if not text.isdigit():
        return None
    score = int(text)
    return score if 1 <= score <= 5 else None


# VERIFIED
def parse_submitted(value):
    """Naive UTC datetime from epoch seconds or one of the text formats."""
    text = clean(value)
    if text.isdigit():
        return datetime.fromtimestamp(int(text), tz=timezone.utc).replace(tzinfo=None)
    for fmt in TEXT_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"unrecognised timestamp: {value!r}")
