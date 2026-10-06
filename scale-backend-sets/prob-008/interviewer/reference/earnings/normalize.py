"""Turn the API's wire values into canonical Python values (PART2.md rules).

Every function either returns the canonical value or raises ``DataError``: a
value we cannot interpret must stop the payout run, not be guessed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

EPOCH_MS_THRESHOLD = 10**11  # epoch numbers at or above this are milliseconds
VERDICTS = ("approved", "rejected")


class DataError(ValueError):
    """A field value that matches none of the documented forms."""


def parse_ts(value: Any) -> datetime:
    """ISO-8601 (Z, offset or naive = UTC) or Unix epoch seconds/milliseconds -> aware UTC datetime."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = value / 1000 if value >= EPOCH_MS_THRESHOLD else value
        return datetime.fromtimestamp(seconds, timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            raise DataError(f"unparseable timestamp {value!r}") from None
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    raise DataError(f"unparseable timestamp {value!r}")


def reward_cents(task: dict) -> int | None:
    """The task's reward in cents, or None when it is unknown (null or missing)."""
    value = task.get("reward_cents")
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise DataError(f"task {task.get('id')}: bad reward_cents {value!r}")


def label(value: Any) -> str | None:
    """Labels and enums compare trimmed and case-insensitively."""
    return value.strip().casefold() if isinstance(value, str) else None


def verdict(value: Any) -> str:
    normalized = label(value)
    if normalized not in VERDICTS:
        raise DataError(f"unknown verdict {value!r}")
    return normalized


def flag(value: Any) -> bool:
    """true/false, "true"/"false" (any case) or 1/0."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    raise DataError(f"bad boolean {value!r}")
