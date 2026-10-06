"""Which failed attempts are retried, and when the retry is due."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import httpx

RETRYABLE_STATUS = frozenset({408, 429})
# Timeouts are retryable too (the mid-Part-2 change): a slow subscriber may still recover.
RETRYABLE_ERRORS = (httpx.ConnectError, httpx.TimeoutException)


def retryable_status(status_code: int) -> bool:
    return status_code in RETRYABLE_STATUS or 500 <= status_code <= 599


def retryable_error(exc: httpx.HTTPError) -> bool:
    return isinstance(exc, RETRYABLE_ERRORS)


def parse_retry_after(response: httpx.Response) -> float | None:
    """Retry-After as whole seconds, or None if absent or not a non-negative integer.

    (The HTTP-date form is treated as unusable; the caller falls back to backoff.)
    """
    value = response.headers.get("Retry-After", "").strip()
    return float(value) if value.isascii() and value.isdigit() else None


@dataclass
class Backoff:
    """Exponential backoff with jitter: min(cap, base * 2**(n-1)) * U[0.5, 1.0]."""

    rng: random.Random = field(default_factory=random.Random)
    base_s: float = 10.0
    cap_s: float = 300.0

    def delay(self, attempt: int) -> float:
        ceiling = min(self.cap_s, self.base_s * 2 ** min(attempt - 1, 32))
        return ceiling * self.rng.uniform(0.5, 1.0)
