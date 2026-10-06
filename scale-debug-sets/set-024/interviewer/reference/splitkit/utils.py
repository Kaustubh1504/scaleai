from datetime import date, datetime

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d %b %Y")


def clean(value):
    return str(value if value is not None else "").strip()


def split_list(value, sep=";"):
    return [part.strip().lower() for part in clean(value).split(sep) if part.strip()]


def parse_bool(value, default=True):
    text = clean(value).lower()
    if not text:
        return default
    return text in {"y", "yes", "true", "1"}


# VERIFIED
def parse_date(value) -> date:
    text = clean(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date: {value!r}")
