"""13. Handle 429 and Retry-After

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import random
from datetime import timezone
from email.utils import parsedate_to_datetime
from typing import Any
import httpx
import datetime

TRANSIENT_STATUSES = frozenset({500, 502, 503, 504})
DEFAULT_WAIT_S = 1.0


class ApiError(Exception):
    def __init__(self, status: int | None, path: str, attempts: int, message: str = ""):
        super().__init__(f"{status} on {path} after {attempts} attempt(s): {message}")
        self.status = status
        self.path = path
        self.attempts = attempts


class RateLimitedError(Exception):
    def __init__(self, path: str, count: int):
        super().__init__(f"{path}: rate limited {count} times in a row, giving up")
        self.path = path
        self.count = count

def _http_date(value):
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replaace(tzinfo=timezone.utc)
    
    return dt.timestamp()



def retry_after_seconds(retry_after: str | None, date: str | None, now: float) -> float:
    value = (retry_after or "").strip()
    
    if value.isdigit() and float(value)>0:
        return float(retry_after)
    
    target = _http_date(value)
    if target is None:
        return DEFAULT_WAIT_S
    server_now = _http_date(date)
    wait = target - (server_now if server_now is not None else now)
    return wait if wait>=0 else DEFAULT_WAIT_S
    
def _backoff(attempt: int, base_s: float, cap_s: float, rng: random.Random) -> float:
    d = min(cap_s, base_s * 2 ** (attempt - 1))
    return rng.uniform(d / 2, d)

def request_respecting_429(client: httpx.Client, method: str, path: str, *,
                           clock: Any, rng: random.Random,
                           max_attempts: int = 4, base_s: float = 0.5, cap_s: float = 8.0,
                           max_429s: int = 5, **kwargs: Any) -> httpx.Response:
    
        attempts = 0
        con_429s = 0
        status = None
        reason = ""
        
        while True:
            try:
                res = client.request(method, path, **kwargs)
            except httpx.TransportError as exc:
                status, reason = None, f"{exc}"
            
            else:
                status = res.status_code
                if status == 429:
                    con_429s+=1
                    if con_429s>max_429s:
                        raise RateLimitedError(path, con_429s)
                    clock.sleep(retry_after_seconds(res.headers.get("Retry-After"),
                                                    res.headers.get("Date"),
                                                    clock.time()
                                                   ))
                    continue
                if res.is_success:
                    try:
                        res.json()
                    except ValueError:
                        reason = "2xx with a body that is not valid JSON"
                    else:
                        return res
                elif status not in TRANSIENT_STATUSES:
                    raise ApiError(status, path, attempts + 1, res.text[:200])
                else:
                    reason = res.text[:200]
            con_429s = 0
            attempts+=1
            if attempts>=max_attempts:
                raise ApiError(status, path, attempts, reason)
            
            clock.sleep(_backoff(attempts, base_s, cap_s, rng))
            


if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import make_api

    clock = FakeClock()
    api = make_api(clock)
    api.script("GET /v1/batches/bat_001", ["429:2", api.too_many_in(5), api.too_many("soon"), 503])
    resp = request_respecting_429(api.client(), "GET", "/v1/batches/bat_001", clock=clock, rng=random.Random(0))
    print(resp.json(), "after", len(api.log), "requests")
    print("slept", [round(s, 3) for s in clock.sleeps])
