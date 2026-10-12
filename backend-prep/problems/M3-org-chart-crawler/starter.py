"""M3. Org chart crawler

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import json
import os
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import httpx
from kit import RealClock

REFRESH_MARGIN_S = 5.0
MAX_429_IN_A_ROW = 5


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


class AuthError(ApiError):
    pass


@dataclass
class CrawlResult:
    order: list[str] = field(default_factory=list)
    headcount: dict[str, int] = field(default_factory=dict)
    dangling: list[str] = field(default_factory=list)
    inaccessible: list[str] = field(default_factory=list)


class OrgClient:
    def __init__(self, http: httpx.Client, client_id: str, client_secret: str, *, clock: Any = None):
        self.http = http
        self.client_id = client_id
        self.client_secret = client_secret
        self.clock = clock if clock is not None else RealClock()
        self._token: str | None = None
        self._expires_at = 0.0
        self._wait_until = 0.0

    def get(self, path: str, params: dict | None = None) -> Any:
        raise NotImplementedError

    def members(self, org_id: str) -> list[dict]:
        raise NotImplementedError


def crawl_org(client: OrgClient, root_id: str, checkpoint_path: str | Path | None = None) -> CrawlResult:
    raise NotImplementedError


if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import CLIENT_ID, CLIENT_SECRET, make_api

    clock = FakeClock()
    api = make_api(clock=clock, auth=True, token_ttl_s=8, latency_s=0.2, rate_limit=3, forbidden={"org_legal"})
    result = crawl_org(OrgClient(api.client(), CLIENT_ID, CLIENT_SECRET, clock=clock), "org_root")
    print("order:", result.order)
    print("headcount:", result.headcount)
    print("dangling:", result.dangling, "inaccessible:", result.inaccessible)
    print(f"{len(api.log)} requests, {api.tokens.issued} tokens, {api.limiter.rejected} x 429, "
          f"slept {clock.total_slept:.1f}s")
