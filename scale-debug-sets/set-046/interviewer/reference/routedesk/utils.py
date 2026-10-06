from datetime import datetime

TIMESTAMP_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return str(value if value is not None else "").strip()


def norm_item(value):
    return clean(value).upper()


def norm_key(value):
    return clean(value).lower()


def parse_timestamp(value):
    text = clean(value)
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"unrecognised timestamp: {value!r}")


# VERIFIED
def parse_confidence(value):
    text = clean(value).rstrip("%").strip()
    if not text:
        return None
    number = float(text)
    # anything above 1 was written as a percentage
    return number / 100 if number > 1 else number
