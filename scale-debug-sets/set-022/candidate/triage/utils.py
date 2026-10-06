from datetime import datetime

TS_FORMATS = ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%d.%m.%Y %H:%M")
TRUTHY = {"y", "yes", "true", "1"}


def clean(value):
    return str(value if value is not None else "").strip()


def split_list(value, sep=";"):
    return [part.strip().lower() for part in clean(value).split(sep) if part.strip()]


def parse_flag(value):
    """Blank means yes; otherwise only the usual truthy spellings count."""
    text = clean(value).lower()
    return text == "" or text in TRUTHY


def parse_float(value):
    text = clean(value)
    return float(text) if text else None


def parse_int(value, default=0):
    text = clean(value)
    return int(text) if text else default


# VERIFIED
def parse_ts(value):
    text = clean(value)
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"unrecognised timestamp: {value!r}")
