"""A mock third-party REST API: OAuth tokens, cursor pagination, 429s, flaky pages.

API
---
POST /oauth/token        {"client_id", "client_secret"}
    200 {"access_token", "token_type": "bearer", "expires_in"}   401 {"error": "invalid_client"}
GET  /v1/records?limit=&cursor=      (Authorization: Bearer <token>)
    200 {"data": [...], "next_cursor": "<opaque>" | null}
    400 {"error": "invalid_cursor" | "invalid_limit"}
    401 {"error": "token_expired" | "invalid_token"}
    429 {"error": "rate_limited"} with a Retry-After header (seconds)
    500/503 {"error": "upstream_error"}
GET  /v1/records/{id}    200 record | 404

Behaviour
---------
* Tokens expire ``token_ttl_s`` after issue (on the API's clock).
  ``expire_all_tokens()`` forces the 401 path immediately.
* Records are returned sorted by ``id``. Cursors are opaque; do not parse them.
* ``rpm_limit`` allows that many record requests per ``window_s``; the rest get
  429 with Retry-After set to when the window frees up.
* ``script_page(offset, [500, 500, 200])`` scripts successive responses for the
  page starting at ``offset`` (first page is offset 0; with limit 20 the second
  page is offset 20). Entries: an int status or ``"429:<seconds>"``.
"""

from __future__ import annotations

import base64
import json
import math
import secrets
import threading
from collections import deque
from dataclasses import dataclass

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response

from ..fake_clock import Clock, RealClock


@dataclass
class RequestLog:
    method: str
    path: str
    params: dict[str, str]
    status: int
    at: float


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"o": offset}).encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> int:
    padded = cursor + "=" * (-len(cursor) % 4)
    offset = json.loads(base64.urlsafe_b64decode(padded.encode()))["o"]
    if not isinstance(offset, int) or offset < 0:
        raise ValueError("bad offset")
    return offset


class MockRecordsAPI:
    def __init__(self, records: list[dict], *, clock: Clock | None = None, client_id: str = "client",
                 client_secret: str = "secret", token_ttl_s: float = 300.0, default_page_size: int = 20,
                 max_page_size: int = 100, rpm_limit: int | None = None, window_s: float = 60.0):
        self.records = sorted(records, key=lambda r: r["id"])
        self.clock = clock or RealClock()
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_ttl_s = token_ttl_s
        self.default_page_size = default_page_size
        self.max_page_size = max_page_size
        self.rpm_limit = rpm_limit
        self.window_s = window_s
        self.tokens: dict[str, float] = {}  # token -> expiry time
        self.tokens_issued = 0
        self.log: list[RequestLog] = []
        self._page_scripts: dict[int, deque] = {}
        self._window: deque[float] = deque()
        self._lock = threading.Lock()

    # ------------------------------------------------------------- controls

    def script_page(self, offset: int, responses: list[int | str]) -> None:
        with self._lock:
            self._page_scripts.setdefault(offset, deque()).extend(str(r) for r in responses)

    def expire_all_tokens(self) -> None:
        with self._lock:
            self.tokens = {t: self.clock.time() - 1 for t in self.tokens}

    def add_record(self, record: dict) -> None:
        with self._lock:
            self.records = sorted([*self.records, record], key=lambda r: r["id"])

    def requests_to(self, path_prefix: str) -> list[RequestLog]:
        return [entry for entry in self.log if entry.path.startswith(path_prefix)]

    # ------------------------------------------------------------- handling

    def _respond(self, request: httpx.Request, status: int, body: dict, headers: dict | None = None) -> httpx.Response:
        self.log.append(RequestLog(request.method, request.url.path, dict(request.url.params), status,
                                   self.clock.time()))
        return httpx.Response(status, json=body, headers=headers or {})

    def _issue_token(self, request: httpx.Request) -> httpx.Response:
        try:
            creds = json.loads(request.content or b"{}")
        except ValueError:
            creds = {}
        if creds.get("client_id") != self.client_id or creds.get("client_secret") != self.client_secret:
            return self._respond(request, 401, {"error": "invalid_client"})
        token = secrets.token_hex(12)
        self.tokens[token] = self.clock.time() + self.token_ttl_s
        self.tokens_issued += 1
        return self._respond(request, 200, {"access_token": token, "token_type": "bearer",
                                            "expires_in": self.token_ttl_s})

    def _auth_error(self, request: httpx.Request) -> str | None:
        header = request.headers.get("authorization", "")
        if not header.lower().startswith("bearer "):
            return "invalid_token"
        expiry = self.tokens.get(header[7:].strip())
        if expiry is None:
            return "invalid_token"
        if self.clock.time() >= expiry:
            return "token_expired"
        return None

    def _rate_limited(self) -> float | None:
        if self.rpm_limit is None:
            return None
        now = self.clock.time()
        while self._window and self._window[0] <= now - self.window_s:
            self._window.popleft()
        if len(self._window) >= self.rpm_limit:
            return self._window[0] + self.window_s - now
        self._window.append(now)
        return None

    def handle(self, request: httpx.Request) -> httpx.Response:
        with self._lock:
            path = request.url.path
            if request.method == "POST" and path == "/oauth/token":
                return self._issue_token(request)
            if not path.startswith("/v1/records") or request.method != "GET":
                return self._respond(request, 404, {"error": "not_found"})
            auth_error = self._auth_error(request)
            if auth_error:
                return self._respond(request, 401, {"error": auth_error})
            wait = self._rate_limited()
            if wait is not None:
                return self._respond(request, 429, {"error": "rate_limited"},
                                     {"Retry-After": str(max(1, math.ceil(wait)))})
            if path != "/v1/records":
                record_id = path.rsplit("/", 1)[-1]
                record = next((r for r in self.records if str(r["id"]) == record_id), None)
                return self._respond(request, 200 if record else 404, record or {"error": "not_found"})
            return self._list(request)

    def _list(self, request: httpx.Request) -> httpx.Response:
        params = request.url.params
        try:
            limit = int(params.get("limit", self.default_page_size))
        except ValueError:
            limit = -1
        if not 1 <= limit <= self.max_page_size:
            return self._respond(request, 400, {"error": "invalid_limit"})
        try:
            offset = decode_cursor(params["cursor"]) if params.get("cursor") else 0
        except (ValueError, KeyError, TypeError):
            return self._respond(request, 400, {"error": "invalid_cursor"})
        script = self._page_scripts.get(offset)
        if script:
            outcome = script.popleft()
            if outcome.startswith("429"):
                return self._respond(request, 429, {"error": "rate_limited"},
                                     {"Retry-After": outcome.partition(":")[2] or "1"})
            if int(outcome) >= 400:
                return self._respond(request, int(outcome), {"error": "upstream_error"})
        page = self.records[offset : offset + limit]
        next_offset = offset + len(page)
        next_cursor = encode_cursor(next_offset) if next_offset < len(self.records) else None
        return self._respond(request, 200, {"data": page, "next_cursor": next_cursor})

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def app(self) -> FastAPI:
        app = FastAPI(title="Mock records API")

        @app.api_route("/{path:path}", methods=["GET", "POST"])
        async def proxy(path: str, request: Request):
            forwarded = httpx.Request(request.method, str(request.url), headers=request.headers.raw,
                                      content=await request.body())
            response = self.handle(forwarded)
            return Response(response.content, status_code=response.status_code,
                            headers={k: v for k, v in response.headers.items() if k.lower() != "content-length"},
                            media_type="application/json")

        return app
