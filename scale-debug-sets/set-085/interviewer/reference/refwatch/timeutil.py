"""Small datetime helpers shared by the rules."""
from datetime import timedelta


# VERIFIED
def within_days(start, end, days):
    """True when `end` is at or after `start` and no more than `days` days later."""
    return timedelta(0) <= end - start <= timedelta(days=days)


def minutes_between(earlier, later):
    """Minutes from `earlier` to `later` (both datetimes)."""
    return (later - earlier).total_seconds() / 60
