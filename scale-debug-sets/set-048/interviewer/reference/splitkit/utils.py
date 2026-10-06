from datetime import datetime

TIMESTAMP_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%d", "%m/%d/%Y")
TRUE_WORDS = {"y", "yes", "true", "1"}


def clean(value):
    return str(value if value is not None else "").strip()


def norm_sample(value):
    return clean(value).upper()


def norm_group(value):
    return clean(value).lower()


def norm_label(value):
    return clean(value).lower()


def parse_flag(value):
    if isinstance(value, str):
        return value.strip().lower() in TRUE_WORDS
    return bool(value)


# VERIFIED
def parse_timestamp(value):
    text = clean(value)
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp: {value!r}")
