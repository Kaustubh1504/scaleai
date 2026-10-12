"""In-process fake HTTP APIs.

A ``MockAPI`` is a tiny router. Register handlers, then hand an
``httpx.Client`` wired to it to the code under test. No sockets, no real
network, deterministic.

    api = MockAPI(clock=clock)

    @api.route("GET", "/users/{user_id}")
    def get_user(req, user_id):
        if user_id not in USERS:
            return 404, {"error": "not found"}
        return USERS[user_id]                    # dict/list -> 200 JSON

    client = api.client()                        # httpx.Client(base_url=BASE_URL)
    client.get("/users/u1").json()

Handlers receive a ``Call`` (method, path, params, headers, body, json()) plus
the path parameters, and return one of:
    * a dict / list               -> 200 JSON
    * (status, body)              -> JSON body (or b""/None for empty)
    * (status, body, headers)
    * an ``httpx.Response``

Fault injection, consumed in order per "METHOD /path" key (or "*" for any):

    api.script("GET /users", [503, "429:2", "timeout", "connect", "malformed", "pass"])

    503 / 500 / ...  -> that status with a JSON error body (handler not called)
    "429:N"          -> 429 with ``Retry-After: N``; "429" -> 429 without it
    "timeout"        -> raises httpx.ReadTimeout
    "connect"        -> raises httpx.ConnectError
    "malformed"      -> runs the real handler (side effects happen!) then
                        returns 200 with a truncated, non-JSON body
    "pass" / 200     -> the real handler
    callable(call)   -> its return value is the response

``api.log`` records every request (``Call`` objects with ``.status`` filled in;
``None`` when a transport error was raised). ``api.calls("GET", "/users")``
filters it.
"""

from __future__ import annotations

import asyncio
import base64
import json
import random
import re
import threading
import time as _time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable
from urllib.parse import parse_qsl

import httpx

BASE_URL = "https://api.example.test"


@dataclass
class Call:
    method: str
    path: str
    params: dict[str, str]
    headers: dict[str, str]  # lower-cased names
    body: bytes
    at: float | None = None
    status: int | None = None  # filled in after the response; None if a transport error was raised
    multi_params: list[tuple[str, str]] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.method} {self.path}"

    def json(self) -> Any:
        if not self.body:
            return None
        return json.loads(self.body)

    def header(self, name: str, default: str | None = None) -> str | None:
        return self.headers.get(name.lower(), default)


def json_response(body: Any, status: int = 200, headers: dict[str, str] | None = None) -> httpx.Response:
    content = b"" if body is None else json.dumps(body).encode()
    hdrs = {"content-type": "application/json"} if body is not None else {}
    hdrs.update(headers or {})
    return httpx.Response(status, content=content, headers=hdrs)


def error_response(status: int, message: str | None = None, headers: dict[str, str] | None = None) -> httpx.Response:
    return json_response({"error": message or _REASONS.get(status, "error")}, status, headers)


_REASONS = {
    400: "bad request", 401: "unauthorized", 403: "forbidden", 404: "not found", 408: "request timeout",
    409: "conflict", 422: "unprocessable entity", 429: "too many requests", 500: "internal server error",
    502: "bad gateway", 503: "service unavailable", 504: "gateway timeout",
}


class MockAPI:
    def __init__(
        self,
        clock: Any = None,
        *,
        latency_s: float = 0.0,
        real_latency_s: float = 0.0,
        base_url: str = BASE_URL,
    ):
        """
        clock          : advanced by ``latency_s`` on every request (use a FakeClock).
        real_latency_s : really sleep this long per request (only for concurrency problems).
        """
        self.clock = clock
        self.latency_s = latency_s
        self.real_latency_s = real_latency_s
        self.base_url = base_url
        self.log: list[Call] = []
        self._routes: list[tuple[str, re.Pattern[str], Callable[..., Any]]] = []
        self._scripts: dict[str, list[Any]] = {}
        self._random_faults: tuple[float, tuple[Any, ...], random.Random] | None = None
        self._lock = threading.Lock()
        self.in_flight = 0
        self.max_in_flight = 0

    # ------------------------------------------------------------ routing

    def route(self, method: str, pattern: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        regex = re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern) + "$")

        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._routes.append((method.upper(), regex, fn))
            return fn

        return deco

    def add_route(self, method: str, pattern: str, fn: Callable[..., Any]) -> None:
        self.route(method, pattern)(fn)

    # ------------------------------------------------------------- faults

    def script(self, key: str, outcomes: Iterable[Any]) -> None:
        """Queue outcomes for requests matching ``key`` ("GET /path" or "*")."""
        with self._lock:
            self._scripts.setdefault(key, []).extend(outcomes)

    def random_faults(self, rate: float, kinds: Iterable[Any] = (500, 503), seed: int = 0) -> None:
        """Each request fails with probability ``rate`` using an outcome drawn from ``kinds``."""
        self._random_faults = (rate, tuple(kinds), random.Random(seed))

    # ------------------------------------------------------------ clients

    def client(self, **kwargs: Any) -> httpx.Client:
        kwargs.setdefault("base_url", self.base_url)
        return httpx.Client(transport=httpx.MockTransport(self._handle_sync), **kwargs)

    def async_client(self, **kwargs: Any) -> httpx.AsyncClient:
        kwargs.setdefault("base_url", self.base_url)
        return httpx.AsyncClient(transport=httpx.MockTransport(self._handle_async), **kwargs)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle_sync)

    # ---------------------------------------------------------- inspection

    def calls(self, method: str | None = None, path: str | None = None) -> list[Call]:
        return [c for c in list(self.log)
                if (method is None or c.method == method.upper()) and (path is None or c.path == path)]

    # ------------------------------------------------------------ handling

    def _handle_sync(self, request: httpx.Request) -> httpx.Response:
        self._enter()
        try:
            if self.real_latency_s:
                _time.sleep(self.real_latency_s)
            return self._dispatch(request)
        finally:
            self._leave()

    async def _handle_async(self, request: httpx.Request) -> httpx.Response:
        self._enter()
        try:
            if self.real_latency_s:
                await asyncio.sleep(self.real_latency_s)
            return self._dispatch(request)
        finally:
            self._leave()

    def _enter(self) -> None:
        with self._lock:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)

    def _leave(self) -> None:
        with self._lock:
            self.in_flight -= 1

    def _dispatch(self, request: httpx.Request) -> httpx.Response:
        if self.clock is not None and self.latency_s:
            self.clock.advance(self.latency_s)
        request.read()
        multi = parse_qsl(request.url.query.decode() if isinstance(request.url.query, bytes) else request.url.query,
                          keep_blank_values=True)
        call = Call(
            method=request.method.upper(),
            path=request.url.path,
            params=dict(multi),
            multi_params=multi,
            headers={k.lower(): v for k, v in request.headers.items()},
            body=request.content,
            at=self.clock.time() if self.clock is not None else None,
        )
        with self._lock:
            self.log.append(call)
            outcome = self._next_outcome(call)

        if outcome == "timeout":
            raise httpx.ReadTimeout("mock: read timed out", request=request)
        if outcome == "connect":
            raise httpx.ConnectError("mock: connection refused", request=request)

        if callable(outcome):
            response = _coerce(outcome(call))
        elif isinstance(outcome, str) and outcome.startswith("429"):
            headers = {"Retry-After": outcome.split(":", 1)[1]} if ":" in outcome else {}
            response = error_response(429, headers=headers)
        elif isinstance(outcome, int) and outcome >= 300:
            response = error_response(outcome)
        else:
            response = self._run_handler(call)
            if outcome == "malformed":
                text = response.content[: max(1, len(response.content) // 2)] or b"{"
                response = httpx.Response(200, content=b'{"truncated": ' + text,
                                          headers={"content-type": "application/json"})
        call.status = response.status_code
        return response

    def _next_outcome(self, call: Call) -> Any:
        for key in (call.key, "*"):
            queue = self._scripts.get(key)
            if queue:
                return queue.pop(0)
        if self._random_faults is not None:
            rate, kinds, rng = self._random_faults
            if rng.random() < rate:
                return rng.choice(kinds)
        return "pass"

    def _run_handler(self, call: Call) -> httpx.Response:
        allowed = []
        for method, regex, fn in self._routes:
            m = regex.match(call.path)
            if not m:
                continue
            if method != call.method:
                allowed.append(method)
                continue
            return _coerce(fn(call, **m.groupdict()))
        if allowed:
            return error_response(405, "method not allowed", {"Allow": ", ".join(sorted(set(allowed)))})
        return error_response(404, f"no route for {call.method} {call.path}")


def _coerce(result: Any) -> httpx.Response:
    if isinstance(result, httpx.Response):
        return result
    if isinstance(result, tuple):
        status, body, *rest = result
        headers = rest[0] if rest else None
        if isinstance(body, (bytes, str)):
            raw = body.encode() if isinstance(body, str) else body
            return httpx.Response(status, content=raw, headers=headers or {})
        return json_response(body, status, headers)
    return json_response(result)


# ---------------------------------------------------------------- pagination


def paginate_pages(items: list[Any], page: int, per_page: int) -> dict[str, Any]:
    """Page-number envelope: {"data": [...], "page", "per_page", "total", "total_pages"} (pages are 1-based)."""
    total_pages = max(1, -(-len(items) // per_page))
    start = (page - 1) * per_page
    return {"data": items[start:start + per_page], "page": page, "per_page": per_page,
            "total": len(items), "total_pages": total_pages}


def paginate_offset(items: list[Any], offset: int, limit: int) -> dict[str, Any]:
    """Offset envelope: {"items": [...], "offset", "limit", "total"}."""
    return {"items": items[offset:offset + limit], "offset": offset, "limit": limit, "total": len(items)}


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> int:
    pad = "=" * (-len(cursor) % 4)
    raw = base64.urlsafe_b64decode(cursor + pad).decode()
    if not raw.startswith("o:"):
        raise ValueError("bad cursor")
    return int(raw[2:])


def paginate_cursor(items: list[Any], cursor: str | None, limit: int) -> dict[str, Any]:
    """Cursor envelope: {"results": [...], "next_cursor": str | None}. Raises ValueError on a bad cursor."""
    start = decode_cursor(cursor) if cursor else 0
    end = start + limit
    return {"results": items[start:end], "next_cursor": encode_cursor(end) if end < len(items) else None}


# ------------------------------------------------------------- auth & limits


class TokenIssuer:
    """Issues bearer tokens that expire after ``ttl_s`` seconds of ``clock.time()``."""

    def __init__(self, clock: Any, ttl_s: float = 3600.0):
        self.clock = clock
        self.ttl_s = ttl_s
        self._tokens: dict[str, float] = {}
        self._n = 0
        self.issued = 0

    def issue(self) -> dict[str, Any]:
        self._n += 1
        self.issued += 1
        token = f"tok_{self._n:05d}"
        self._tokens[token] = self.clock.time() + self.ttl_s
        return {"access_token": token, "token_type": "bearer", "expires_in": self.ttl_s}

    def valid(self, authorization: str | None) -> bool:
        if not authorization or not authorization.startswith("Bearer "):
            return False
        exp = self._tokens.get(authorization[len("Bearer "):])
        return exp is not None and self.clock.time() < exp

    def revoke_all(self) -> None:
        self._tokens.clear()


class FixedWindowLimiter:
    """``limit`` requests per ``window_s`` window of ``clock.time()``.

    check() -> (allowed, headers) where headers carry X-RateLimit-Limit/Remaining/Reset
    and, when not allowed, Retry-After (whole seconds, rounded up).
    """

    def __init__(self, clock: Any, limit: int, window_s: float = 1.0):
        self.clock = clock
        self.limit = limit
        self.window_s = window_s
        self._window: int | None = None
        self._count = 0
        self.rejected = 0

    def check(self) -> tuple[bool, dict[str, str]]:
        now = self.clock.time()
        window = int(now // self.window_s)
        if window != self._window:
            self._window = window
            self._count = 0
        reset = (window + 1) * self.window_s
        allowed = self._count < self.limit
        if allowed:
            self._count += 1
        else:
            self.rejected += 1
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.limit - self._count)),
            "X-RateLimit-Reset": f"{reset:.3f}".rstrip("0").rstrip("."),
        }
        if not allowed:
            headers["Retry-After"] = str(max(1, int(-(-(reset - now) // 1))))
        return allowed, headers
