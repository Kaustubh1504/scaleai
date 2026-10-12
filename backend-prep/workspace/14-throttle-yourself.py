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
        self.remaining: int | None = None
        self.reset: float | None = None

    def request(self, method, path, **kwargs):
        # 1. If the server said we have 0 requests left, sleep until the reset time.
        if self.remaining == 0 and self.reset is not None:
            wait = self.reset - self.clock.time()
            if wait > 0:
                self.clock.sleep(wait)
 
        # 2. Send the request.
        resp = self.client.request(method, path, **kwargs)
 
        # 3. Remember the new limits (skip if the headers are missing or broken).
        try:
            remaining = int(resp.headers["X-RateLimit-Remaining"])
            reset = float(resp.headers["X-RateLimit-Reset"])
            self.remaining, self.reset = remaining, reset
        except (KeyError, ValueError):
            pass
        return resp
 
    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)


class TokenBucket:
    """Starts full with ``burst`` tokens and refills continuously at ``rate_per_s``."""

    def __init__(self, rate_per_s: float, burst: int, clock: Any):
        self.rate = float(rate_per_s)
        self.burst = float(burst)
        self.clock = clock
        self.tokens = float(burst)
        self.updated = clock.time()
    
    def acquire(self):
        # 1. Add the tokens that dripped in since last time (never above burst).
        now = self.clock.time()
        self.tokens = min(self.burst, self.tokens + (now - self.updated) * self.rate)
        self.updated = now
 
        # 2. Empty? Sleep until exactly one token has dripped in.
        if self.tokens < 1:
            self.clock.sleep((1 - self.tokens) / self.rate)
            self.tokens = 1
            self.updated = self.clock.time()
 
        # 3. Spend one token.
        self.tokens -= 1


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
