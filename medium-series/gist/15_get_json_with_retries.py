# 15. GET JSON from a flaky, rate-limited API (429s don't burn retries)
# Standalone: copy this file as-is. Deps: stdlib + httpx

import random
import time
from email.utils import parsedate_to_datetime

import httpx


class ApiError(Exception):
    def __init__(self, status, url: str, detail: str = ""):
        super().__init__(f"{status} {url} {detail}".strip())
        self.status, self.url = status, url


def get_json_with_retries(http: httpx.Client, method: str, url: str, *, attempts: int = 4, max_429: int = 10,
                          transient=(500, 502, 503, 504), sleep=time.sleep, rng=random.random, **kwargs):
    """Parsed JSON of a 2xx response.
    Transient failures (transient statuses, transport errors, 2xx with a body that isn't JSON) share `attempts`;
    before attempt n+1 wait uniform[d/2, d], d = min(8, 0.5 * 2**(n-1)).
    429: wait Retry-After (seconds or HTTP date vs Date header; 1s if missing). Doesn't use up `attempts`;
    ApiError after `max_429` 429s in a row. Any other status: ApiError right away (check e.status, e.g. 401)."""
    kwargs.setdefault("timeout", 10)
    failures, in_a_row = 0, 0
    while True:
        r, problem = None, ""
        try:
            r = http.request(method, url, **kwargs)
        except httpx.TransportError as e:
            problem = type(e).__name__
        if r is not None and r.status_code == 429:
            in_a_row += 1
            if in_a_row >= max_429:
                raise ApiError(429, url, f"{in_a_row} rate limits in a row")
            value = r.headers.get("Retry-After", "").strip()
            wait = 1.0
            if value.isdigit():
                wait = float(value)
            elif value:
                try:
                    base = parsedate_to_datetime(r.headers["Date"]).timestamp() if "Date" in r.headers else time.time()
                    wait = max(0.0, parsedate_to_datetime(value).timestamp() - base)
                except (TypeError, ValueError, IndexError):
                    pass
            sleep(wait)
            continue
        in_a_row = 0
        if r is not None and 200 <= r.status_code < 300:
            try:
                return r.json()
            except ValueError:
                problem = "invalid JSON body"
        elif r is not None and r.status_code not in transient:
            raise ApiError(r.status_code, url, r.text[:200])
        failures += 1
        if failures >= attempts:
            raise ApiError(r.status_code if r is not None else None, url, problem or "transient failure")
        d = min(8.0, 0.5 * 2 ** (failures - 1))
        sleep(d / 2 + (d / 2) * rng())
