"""12. Retries with exponential backoff

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import random
from typing import Any
import httpx

TRANSIENT_STATUSES = frozenset({500, 502, 503, 504})


class ApiError(Exception):
    def __init__(self, status: int | None, path: str, attempts: int, message: str = ""):
        super().__init__(f"{status} on {path} after {attempts} attempt(s): {message}")
        self.status = status
        self.path = path
        self.attempts = attempts


def backoff_delay(attempt: int, base_s: float, cap_s: float, rng: random.Random) -> float:
    """Jittered delay after failed attempt ``attempt`` (1-based)."""
    n = attempt
    d = min(cap_s, base_s * 2 ** (n - 1))
    delay = rng.uniform(d / 2, d)
    return delay
    


def request_with_retries(client: httpx.Client, method: str, path: str, *,
                         clock: Any, rng: random.Random,
                         max_attempts: int = 4, base_s: float = 0.5, cap_s: float = 8.0,
                         **kwargs: Any) -> httpx.Response:
       
    status: int | None = None
    reason = ""
    for attempt in range(1, max_attempts+1):
        try:
            res = client.request(method, path, **kwargs)
        except httpx.TransportError as exc:
            status, reason = None, f"{type(exc).__name__}:{exc}"
        else:
            status = res.status_code
            if res.is_success:
                try:
                    res.json()
                except ValueError:
                    reason = "2XX with a invalid json body"
                else:
                    return res
                
            elif status in TRANSIENT_STATUSES:
                reason = res.text[:200]
            else:
                raise ApiError(status, path, attempt, res.text[:200])
        
        
        
        if attempt < max_attempts:
            clock.sleep(backoff_delay(attempt, base_s, cap_s, rng))
    
    
    raise  ApiError(status, path, max_attempts, reason)
               
    

if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import make_api

    api = make_api()
    api.script("GET /v1/tasks/task_001", [503, "timeout", "malformed", "pass"])
    clock = FakeClock()
    resp = request_with_retries(api.client(), "GET", "/v1/tasks/task_001", clock=clock, rng=random.Random(0))
    print(resp.json(), "after", len(api.log), "requests")
    print("slept", [round(s, 3) for s in clock.sleeps])
