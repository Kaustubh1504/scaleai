from datetime import datetime, timedelta

TS_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def parse_ts(value):
    text = (value or "").strip()
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp {value!r}")


def claim_deadline(claim_at, ttl_minutes):
    return claim_at + timedelta(minutes=ttl_minutes)


def claim_expired(deadline, now):
    return now > deadline
