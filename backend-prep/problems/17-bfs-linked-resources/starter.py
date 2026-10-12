"""17. Crawl linked resources with BFS

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from collections import deque
import httpx


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


def fetch_org(client: httpx.Client, org_id: str) -> dict | None:
    """The org, or None on 404. Other errors raise."""
    raise NotImplementedError


def collect_teams(client: httpx.Client, root_id: str, max_depth: int | None = None) -> dict:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import make_api

    api = make_api()
    print(collect_teams(api.client(), "org_acme"))
    print("requests:", len(api.log))
    print("depth 1:", collect_teams(make_api().client(), "org_acme", max_depth=1))
