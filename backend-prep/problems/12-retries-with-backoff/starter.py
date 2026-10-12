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
    raise NotImplementedError


def request_with_retries(client: httpx.Client, method: str, path: str, *,
                         clock: Any, rng: random.Random,
                         max_attempts: int = 4, base_s: float = 0.5, cap_s: float = 8.0,
                         **kwargs: Any) -> httpx.Response:
    raise NotImplementedError


if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import make_api

    api = make_api()
    api.script("GET /v1/tasks/task_001", [503, "timeout", "malformed", "pass"])
    clock = FakeClock()
    resp = request_with_retries(api.client(), "GET", "/v1/tasks/task_001", clock=clock, rng=random.Random(0))
    print(resp.json(), "after", len(api.log), "requests")
    print("slept", [round(s, 3) for s in clock.sleeps])
