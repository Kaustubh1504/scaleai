"""09. Cursor pagination with a loop guard

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

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
    raise NotImplementedError


def fetch_all_events(client: httpx.Client, api_key: str, limit: int = 50) -> list[dict]:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import API_KEY, make_api

    api = make_api(n_events=7)
    events = fetch_all_events(api.client(), API_KEY, limit=3)
    print(len(events), "events in", len(api.log), "requests")
