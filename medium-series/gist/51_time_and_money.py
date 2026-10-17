# 51. Fake HTTP server: scripted replies, call counting, max concurrency
# Standalone: copy this file as-is. Deps: stdlib

from collections import Counter
from datetime import timezone
from decimal import ROUND_HALF_UP, Decimal


def count_per_local_day(timestamps, tz=timezone.utc) -> dict:
    """Aware datetimes (store UTC) -> {"YYYY-MM-DD": count} in the given timezone."""
    return dict(Counter(ts.astimezone(tz).date().isoformat() for ts in timestamps))


def cents_to_dollars(cents: int) -> Decimal:
    """Keep money as integer cents; convert/round once at the end."""
    return (Decimal(cents) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
