"""Mutant m8: backoff does not grow."""

from __future__ import annotations

import httpx

RETRY_STATUSES = {429, 503}


class ApiError(Exception):
    def __init__(self, status: int):
        super().__init__(f"API returned {status}")
        self.status = status


def _delay(resp: httpx.Response, attempt: int, base_delay_s: float) -> float:
    retry_after = resp.headers.get("Retry-After")
    if resp.status_code == 429 and retry_after is not None:
        return float(retry_after)
    return base_delay_s


def _get_page(client: httpx.Client, clock, page: int, max_attempts: int, base_delay_s: float) -> dict:
    for attempt in range(1, max_attempts + 1):
        resp = client.get("/v1/labels", params={"page": page})
        if resp.is_success:
            return resp.json()
        if resp.status_code not in RETRY_STATUSES or attempt == max_attempts:
            raise ApiError(resp.status_code)
        clock.sleep(_delay(resp, attempt, base_delay_s))
    raise AssertionError("unreachable")


def fetch_all(client: httpx.Client, clock, *, max_attempts: int = 4, base_delay_s: float = 0.5) -> list[dict]:
    items: list[dict] = []
    page: int | None = 1
    while page is not None:
        body = _get_page(client, clock, page, max_attempts, base_delay_s)
        items.extend(body["data"])
        page = body["next_page"]
    return items
