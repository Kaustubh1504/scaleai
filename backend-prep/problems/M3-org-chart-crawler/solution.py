"""M3. Org chart crawler: reference solution."""

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
        self.creds = {"client_id": client_id, "client_secret": client_secret}
        self.clock = clock or RealClock()
        self.token = None
        self.expires_at = 0.0
        self.wait_until = 0.0

    def ensure_token(self, force: bool = False) -> str:
        if force or self.token is None or self.clock.time() >= self.expires_at - REFRESH_MARGIN_S:
            resp = self.http.post("/oauth/token", json=self.creds)
            if not resp.is_success:
                raise AuthError(resp.status_code, "/oauth/token", resp.text)
            body = resp.json()
            self.token = body["access_token"]
            self.expires_at = self.clock.time() + body["expires_in"]
        return self.token

    def get(self, path: str, params: dict | None = None) -> Any:
        refreshed, throttled = False, 0
        while True:
            if self.wait_until > self.clock.time():
                self.clock.sleep(self.wait_until - self.clock.time())
            headers = {"Authorization": f"Bearer {self.ensure_token()}"}
            resp = self.http.get(path, params=params, headers=headers)
            if resp.headers.get("X-RateLimit-Remaining") == "0" and "X-RateLimit-Reset" in resp.headers:
                self.wait_until = float(resp.headers["X-RateLimit-Reset"])
            if resp.status_code == 429:
                throttled += 1
                if throttled >= MAX_429_IN_A_ROW:
                    raise ApiError(429, path, "rate limited")
                self.clock.sleep(float(resp.headers.get("Retry-After", "1")))
            elif resp.status_code == 401:
                if refreshed:
                    raise AuthError(401, path, "unauthorized after a token refresh")
                refreshed = True
                self.ensure_token(force=True)
            elif not resp.is_success:
                raise ApiError(resp.status_code, path, resp.text)
            else:
                return resp.json()

    def members(self, org_id: str) -> list[dict]:
        out, params = [], {"limit": 50}
        while True:
            body = self.get(f"/v1/orgs/{org_id}/members", params)
            out += body["results"]
            if not body.get("next_cursor"):
                return out
            params = {"limit": 50, "cursor": body["next_cursor"]}


def crawl_org(client: OrgClient, root_id: str, checkpoint_path: str | Path | None = None) -> CrawlResult:
    ckpt = Path(checkpoint_path) if checkpoint_path else None
    if ckpt and ckpt.exists():
        state = json.loads(ckpt.read_text())
    else:
        state = {"queue": [root_id], "seen": [root_id], "order": [], "children": {},
                 "members": {}, "dangling": [], "inaccessible": []}
    queue, seen = deque(state["queue"]), set(state["seen"])

    while queue:
        org_id = queue[0]  # only dequeue once the org is fully done
        try:
            org = client.get(f"/v1/orgs/{org_id}")
            people = client.members(org_id)
        except ApiError as exc:
            if org_id == root_id or exc.status not in (403, 404):
                raise
            state["dangling" if exc.status == 404 else "inaccessible"].append(org_id)
        else:
            state["order"].append(org_id)
            state["children"][org_id] = org["children"]
            state["members"][org_id] = [p["person_id"] for p in people]
            for child in org["children"]:
                if child not in seen:
                    seen.add(child)
                    queue.append(child)
        queue.popleft()
        state["queue"], state["seen"] = list(queue), list(seen)
        if ckpt:
            tmp = ckpt.with_name(ckpt.name + ".tmp")
            tmp.write_text(json.dumps(state))
            os.replace(tmp, ckpt)

    if ckpt:
        ckpt.unlink(missing_ok=True)

    children, members = state["children"], state["members"]
    headcount = {}
    for org in state["order"]:
        reach, stack = {org}, [org]
        while stack:
            for child in children[stack.pop()]:
                if child in children and child not in reach:
                    reach.add(child)
                    stack.append(child)
        headcount[org] = len({p for o in reach for p in members[o]})
    return CrawlResult(state["order"], headcount, sorted(state["dangling"]),
                       sorted(state["inaccessible"]))


if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import CLIENT_ID, CLIENT_SECRET, make_api

    clock = FakeClock()
    api = make_api(clock=clock, auth=True, token_ttl_s=8, latency_s=0.2, rate_limit=3,
                   forbidden={"org_legal"})
    result = crawl_org(OrgClient(api.client(), CLIENT_ID, CLIENT_SECRET, clock=clock), "org_root")
    print(result)
    print(f"{len(api.log)} requests, {api.tokens.issued} tokens, {api.limiter.rejected} x 429")
