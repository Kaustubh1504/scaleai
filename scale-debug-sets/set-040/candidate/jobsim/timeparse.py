import re

DURATION = re.compile(r"^(?:(\d+)h)?(?:(\d+)m)?$")


def parse_clock(text):
    """'06:05' / '6:05' -> minutes after midnight. Blank -> None."""
    value = (text or "").strip()
    if not value:
        return None
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def fmt_clock(minutes):
    if minutes is None:
        return None
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# VERIFIED
def parse_duration(text):
    """'45m', '1h', '1h30m' or a bare number of minutes -> minutes."""
    value = text.strip().lower()
    if value.isdigit():
        return int(value)
    match = DURATION.match(value)
    if not match or not any(match.groups()):
        raise ValueError(f"bad duration {text!r}")
    hours, minutes = match.groups()
    return int(hours or 0) * 60 + int(minutes or 0)
