from __future__ import annotations

from datetime import datetime, timedelta

_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def parse_datetime(value: str) -> datetime:
    text = value.strip()
    for fmt in _FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp: {value!r}")


def parse_deadline(value: str, run_start: datetime) -> datetime | None:
    """`HH:MM` on the run day, or blank for no deadline."""
    text = (value or "").strip()
    if not text:
        return None
    hours, minutes = (int(p) for p in text.split(":"))
    return run_start.replace(hour=hours, minute=minutes)


def minutes_between(earlier: datetime, later: datetime) -> int:
    return int((later - earlier).seconds // 60)


def clock(dt: datetime | None) -> str | None:
    return None if dt is None else dt.strftime("%H:%M")


def plus_minutes(dt: datetime, minutes: int) -> datetime:
    return dt + timedelta(minutes=minutes)
