"""09. Cursor pagination with a loop guard: reference solution."""

from __future__ import annotations

from typing import Iterator

import httpx


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


class PaginationLoopError(Exception):
    pass


def iter_events(client: httpx.Client, api_key: str, limit: int = 50) -> Iterator[dict]:
    params = {"limit": limit}
    seen = set()
    while True:
        resp = client.get("/v1/events", params=params, headers={"X-API-Key": api_key})
        if not resp.is_success:
            raise ApiError(resp.status_code, "/v1/events", resp.text)
        body = resp.json()
        yield from body["results"]
        cursor = body.get("next_cursor")
        if cursor is None:
            return
        if cursor in seen:
            raise PaginationLoopError(f"server repeated cursor {cursor!r}")
        seen.add(cursor)
        params["cursor"] = cursor


def fetch_all_events(client: httpx.Client, api_key: str, limit: int = 50) -> list[dict]:
    return list(iter_events(client, api_key, limit))


if __name__ == "__main__":
    from problem_api import API_KEY, make_api

    api = make_api(n_events=7)
    events = fetch_all_events(api.client(), API_KEY, limit=3)
    print(len(events), "events in", len(api.log), "requests")
