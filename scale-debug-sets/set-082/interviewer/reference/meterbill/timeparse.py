from datetime import datetime, timezone

SLASH_FORMAT = "%m/%d/%Y %H:%M:%S"


# VERIFIED
def parse_ts(value):
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        stamp = datetime.fromisoformat(text)
    except ValueError:
        stamp = datetime.strptime(text, SLASH_FORMAT)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def parse_month(value):
    text = value.strip()
    if "/" in text:
        month, year = text.split("/")
        return f"{int(year):04d}-{int(month):02d}"
    year, month = text.split("-")
    return f"{int(year):04d}-{int(month):02d}"


def month_of(stamp):
    return stamp.strftime("%Y-%m")


def chronological(requests):
    """Oldest first; requests logged in the same instant keep their log order."""
    return sorted(requests, key=lambda r: r.ts)
