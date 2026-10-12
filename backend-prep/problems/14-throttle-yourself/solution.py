"""14. Throttle yourself: reference solution."""

from __future__ import annotations

from typing import Any

import httpx


class ThrottledClient:
    def __init__(self, client: httpx.Client, clock: Any):
        self.client = client
        self.clock = clock
        self.remaining: int | None = None
        self.reset = 0.0

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        wait = self.reset - self.clock.time()
        if self.remaining == 0 and wait > 0:
            self.clock.sleep(wait)
        resp = self.client.request(method, path, **kwargs)
        h = resp.headers
        try:
            self.remaining, self.reset = (int(h["X-RateLimit-Remaining"]),
                                          float(h["X-RateLimit-Reset"]))
        except (KeyError, ValueError):
            pass
        return resp

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", path, **kwargs)


class TokenBucket:
    def __init__(self, rate_per_s: float, burst: int, clock: Any):
        self.rate = rate_per_s
        self.burst = burst
        self.clock = clock
        self.tokens = float(burst)
        self.updated = clock.time()

    def acquire(self) -> None:
        now = self.clock.time()
        self.tokens = min(self.burst, self.tokens + (now - self.updated) * self.rate)
        if self.tokens < 1:
            self.clock.sleep((1 - self.tokens) / self.rate)
            self.tokens = 1.0
        self.tokens -= 1
        self.updated = self.clock.time()


if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import make_api

    clock = FakeClock()
    api = make_api(clock)
    tc = ThrottledClient(api.client(), clock)
    statuses = [tc.get(f"/v1/annotations/ann_{i:03d}").status_code for i in range(1, 51)]
    print("429s:", statuses.count(429), "| slept", round(clock.total_slept, 3), "s")

    clock2 = FakeClock()
    bucket = TokenBucket(rate_per_s=2, burst=3, clock=clock2)
    for _ in range(6):
        bucket.acquire()
    print("bucket sleeps:", clock2.sleeps)
