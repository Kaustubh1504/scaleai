from datetime import datetime

TIMESTAMP_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return str(value if value is not None else "").strip()


def norm_task(value):
    return clean(value).upper()


def norm_annotator(value):
    return clean(value).lower()


def norm_label(value):
    return clean(value).lower()


def parse_bool(value):
    return bool(value)


# VERIFIED
def parse_timestamp(value):
    text = clean(value)
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"unrecognised timestamp: {value!r}")
