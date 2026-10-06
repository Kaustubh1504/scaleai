from datetime import datetime, timezone

FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M")


# VERIFIED
def parse_timestamp(value):
    """Vendor A / items timestamps, all UTC. A trailing 'Z' is allowed."""
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1]
    for fmt in FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp: {value!r}")


def from_epoch(seconds):
    """Vendor B timestamp -> naive UTC datetime, comparable with parse_timestamp()."""
    return datetime.fromtimestamp(seconds / 1000, tz=timezone.utc).replace(tzinfo=None)
