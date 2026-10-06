from datetime import datetime

from .models import RowError

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return (value or "").strip()


def parse_bool(value):
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1"}
    return bool(value)


# VERIFIED
def parse_price(text):
    """'$1,249.00' -> 124900 cents. None when blank or not a number."""
    text = clean(text).replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        return round(float(text) * 100)
    except ValueError:
        return None


def parse_qty(text):
    text = clean(text)
    if not text:
        return 0
    try:
        qty = int(text)
    except ValueError:
        raise RowError("bad_qty") from None
    if qty < 0:
        raise RowError("bad_qty")
    return qty


def parse_updated(text):
    text = clean(text)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise RowError("bad_date")
