# 20. Scheduled retries (no sleeping): classify, back off, dead-letter
# Standalone: copy this file as-is. Deps: stdlib + httpx

import random
import time
from email.utils import parsedate_to_datetime

import httpx


def classify_attempt(response=None, error=None,
                     retry_statuses=(408, 429), retry_errors=(httpx.ConnectError, httpx.TimeoutException)) -> str:
    """'ok' (2xx) | 'retry' (408, 429, 5xx, connection/timeout errors) | 'dead' (anything else)."""
    if error is not None:
        return "retry" if isinstance(error, retry_errors) else "dead"
    if 200 <= response.status_code < 300:
        return "ok"
    if response.status_code in retry_statuses or response.status_code >= 500:
        return "retry"
    return "dead"


def parse_retry_after(response):
    """Seconds from Retry-After: an integer, or an HTTP date minus the response's Date header. None if unusable."""
    value = response.headers.get("Retry-After", "").strip()
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value).timestamp()
    except (TypeError, ValueError, IndexError):
        return None
    try:
        base = parsedate_to_datetime(response.headers["Date"]).timestamp()
    except (KeyError, TypeError, ValueError, IndexError):
        base = time.time()
    return max(0.0, when - base)


def next_attempt_at(now: float, attempt: int, base: float = 10.0, cap: float = 300.0,
                    retry_after=None, rng=random.random) -> float:
    """After failed attempt number `attempt` (1-based): Retry-After wins exactly; otherwise
    now + min(cap, base * 2**(attempt-1)) * jitter, jitter uniform in [0.5, 1.0]."""
    if retry_after is not None:
        return now + retry_after
    return now + min(cap, base * 2 ** (attempt - 1)) * (0.5 + 0.5 * rng())


def record_attempt(delivery: dict, now: float, response=None, error=None, max_attempts: int = 5, **backoff) -> str:
    """Update {status, attempts, next_attempt_at, last_error} after one attempt; returns the new status."""
    delivery["attempts"] = delivery.get("attempts", 0) + 1
    outcome = classify_attempt(response, error)
    if outcome == "ok":
        delivery.update(status="delivered", next_attempt_at=None, last_error=None)
    else:
        delivery["last_error"] = f"HTTP {response.status_code}" if error is None else type(error).__name__
        if outcome == "dead" or delivery["attempts"] >= max_attempts:
            delivery.update(status="dead", next_attempt_at=None)
        else:
            ra = parse_retry_after(response) if response is not None and response.status_code == 429 else None
            delivery.update(status="pending",
                            next_attempt_at=next_attempt_at(now, delivery["attempts"], retry_after=ra, **backoff))
    return delivery["status"]


def due(deliveries, now: float) -> list:
    return [d for d in deliveries if d["status"] == "pending" and (d.get("next_attempt_at") or 0) <= now]
