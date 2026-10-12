"""14. Throttle yourself: rate-limit headers and a token bucket

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from typing import Any
import httpx


class ThrottledClient:
    """Wraps an httpx.Client and waits out the server's window before it can 429 us."""

    def __init__(self, client: httpx.Client, clock: Any):
        self.client = client
        self.clock = clock
        self._remaining: int | None = None
        self._reset: float | None = None

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        raise NotImplementedError

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        raise NotImplementedError


class TokenBucket:
    """Starts full with ``burst`` tokens and refills continuously at ``rate_per_s``."""

    def __init__(self, rate_per_s: float, burst: int, clock: Any):
        self.rate = float(rate_per_s)
        self.burst = float(burst)
        self.clock = clock
        self.tokens = float(burst)
        self._updated = clock.time()

    def acquire(self) -> None:
        raise NotImplementedError


if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import make_api

    clock = FakeClock()
    api = make_api(clock)
    tc = ThrottledClient(api.client(), clock)
    statuses = [tc.get(f"/v1/annotations/ann_{i:03d}").status_code for i in range(1, 51)]
    print("429s:", statuses.count(429), "| slept", round(clock.total_slept, 3), "s in", len(clock.sleeps), "sleeps")

    clock2 = FakeClock()
    bucket = TokenBucket(rate_per_s=2, burst=3, clock=clock2)
    for _ in range(6):
        bucket.acquire()
    print("bucket sleeps:", clock2.sleeps)
