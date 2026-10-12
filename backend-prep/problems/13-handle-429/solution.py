"""13. Handle 429 and Retry-After: reference solution."""

from __future__ import annotations

import random
from datetime import timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx


class ApiError(Exception):
    def __init__(self, status: int | None, path: str, attempts: int, message: str = ""):
        super().__init__(f"{status} on {path} after {attempts} attempt(s): {message}")
        self.status = status
        self.path = path
        self.attempts = attempts


class RateLimitedError(Exception):
    def __init__(self, path: str, count: int):
        super().__init__(f"{path}: rate limited {count} times in a row")
        self.path = path
        self.count = count


def _http_date(value: str | None) -> float | None:
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return dt.replace(tzinfo=dt.tzinfo or timezone.utc).timestamp()


def retry_after_seconds(retry_after: str | None, date: str | None, now: float) -> float:
    value = (retry_after or "").strip()
    if value.isdigit():
        return float(value)
    target = _http_date(value)
    if target is None:
        return 1.0
    server_now = _http_date(date)
    wait = target - (now if server_now is None else server_now)
    return wait if wait >= 0 else 1.0


def request_respecting_429(client: httpx.Client, method: str, path: str, *,
                           clock: Any, rng: random.Random,
                           max_attempts: int = 4, base_s: float = 0.5, cap_s: float = 8.0,
                           max_429s: int = 5, **kwargs: Any) -> httpx.Response:
    attempts = streak = 0
    while True:
        try:
            resp = client.request(method, path, **kwargs)
        except httpx.TransportError as exc:
            status, reason = None, repr(exc)
        else:
            status, reason = resp.status_code, resp.text[:200]
            if status == 429:
                streak += 1
                if streak > max_429s:
                    raise RateLimitedError(path, streak)
                h = resp.headers
                clock.sleep(retry_after_seconds(h.get("Retry-After"), h.get("Date"), clock.time()))
                continue
            if resp.is_success:
                try:
                    resp.json()
                    return resp
                except ValueError:
                    reason = "2xx with a non-JSON body"
            elif status not in (500, 502, 503, 504):
                raise ApiError(status, path, attempts + 1, reason)
        streak = 0
        attempts += 1
        if attempts >= max_attempts:
            raise ApiError(status, path, attempts, reason)
        d = min(cap_s, base_s * 2 ** (attempts - 1))
        clock.sleep(rng.uniform(d / 2, d))


if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import make_api

    clock = FakeClock()
    api = make_api(clock)
    api.script("GET /v1/batches/bat_001", ["429:2", api.too_many_in(5), api.too_many("soon"), 503])
    resp = request_respecting_429(api.client(), "GET", "/v1/batches/bat_001", clock=clock,
                                  rng=random.Random(0))
    print(resp.json(), "after", len(api.log), "requests; slept", clock.sleeps)
