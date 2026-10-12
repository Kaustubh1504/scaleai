"""12. Retries with exponential backoff: reference solution."""

from __future__ import annotations

import random

import httpx


class ApiError(Exception):
    def __init__(self, status: int | None, path: str, attempts: int, message: str = ""):
        super().__init__(f"{status} on {path} after {attempts} attempt(s): {message}")
        self.status = status
        self.path = path
        self.attempts = attempts


def request_with_retries(client: httpx.Client, method: str, path: str, *, clock,
                         rng: random.Random, max_attempts: int = 4, base_s: float = 0.5,
                         cap_s: float = 8.0, **kwargs) -> httpx.Response:
    for attempt in range(1, max_attempts + 1):
        try:
            resp = client.request(method, path, **kwargs)
        except httpx.TransportError:
            status = None
        else:
            status = resp.status_code
            if resp.is_success:
                try:
                    resp.json()
                    return resp
                except ValueError:  # truncated body: the server was mid-write, worth another go
                    pass
            elif status not in (500, 502, 503, 504):
                raise ApiError(status, path, attempt)
        if attempt < max_attempts:
            d = min(cap_s, base_s * 2 ** (attempt - 1))
            clock.sleep(rng.uniform(d / 2, d))
    raise ApiError(status, path, max_attempts)


if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import make_api

    api = make_api()
    api.script("GET /v1/tasks/task_001", [503, "timeout", "malformed", "pass"])
    clock = FakeClock()
    resp = request_with_retries(api.client(), "GET", "/v1/tasks/task_001", clock=clock,
                                rng=random.Random(0))
    print(resp.json(), "after", len(api.log), "requests; slept", [round(s, 3) for s in clock.sleeps])
