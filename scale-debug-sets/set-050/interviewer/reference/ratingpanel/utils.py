from datetime import datetime

TIMESTAMP_FORMATS = ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S")
MIN_RATING, MAX_RATING = 1, 10


def clean(value):
    return str(value if value is not None else "").strip()


def norm_item(value):
    return clean(value).upper()


def norm_annotator(value):
    return clean(value).lower()


def parse_timestamp(value):
    text = clean(value)
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"unrecognised timestamp: {value!r}")


def duration_seconds(started_at, finished_at):
    return (finished_at - started_at).total_seconds()


# VERIFIED
def parse_rating(value):
    text = clean(value)
    if not text:
        return None
    rating = int(float(text))
    if not MIN_RATING <= rating <= MAX_RATING:
        return None
    return rating
