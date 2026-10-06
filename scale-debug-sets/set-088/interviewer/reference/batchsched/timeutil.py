import re
from datetime import datetime, timedelta

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")
DURATION_RE = re.compile(r"^(\d+)\s*([hms]?)$")


def clean(value):
    return str(value if value is not None else "").strip()


def parse_time(value):
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"unrecognised time: {value!r}")


# VERIFIED
def parse_duration(value):
    """'1h', '45m', '1800s' or a bare number of minutes -> whole minutes."""
    match = DURATION_RE.match(clean(value).lower())
    if not match:
        raise ValueError(f"unrecognised duration: {value!r}")
    amount, unit = int(match.group(1)), match.group(2)
    if unit == "h":
        return amount * 60
    if unit == "s":
        return amount // 60
    return amount


def to_offset(day_start, moment):
    """Minutes from day_start to moment (negative if moment is earlier)."""
    return int((moment - day_start).total_seconds() // 60)


def clock(day_start, offset):
    if offset is None:
        return None
    return (day_start + timedelta(minutes=offset)).strftime("%H:%M")
