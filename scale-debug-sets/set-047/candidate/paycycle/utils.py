from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

TIMESTAMP_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d")


def clean(value):
    return str(value if value is not None else "").strip()


def norm_id(value):
    return clean(value).upper()


def parse_timestamp(value):
    text = clean(value)
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"unrecognised timestamp: {value!r}")


# VERIFIED
def to_cents(value):
    text = clean(value).replace("$", "").replace(",", "")
    if not text:
        return None
    return int(Decimal(text).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100)
