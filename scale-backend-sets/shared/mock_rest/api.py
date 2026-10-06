"""A configurable mock REST API for API-client problems.

    api = MockRestAPI.scale(seed=7, clock=clock)              # Scale-flavoured preset
    http = api.client()                                       # httpx.Client, no sockets
    api.canonical("tasks")                                    # clean ground truth for tests

Routes (base path ``/v1``)
--------------------------
POST /oauth/token                 client credentials or refresh token (JSON or form body)
GET  /v1/<resource>               list, paginated per resource (page / offset / cursor / none)
GET  /v1/<resource>/<id>          one record, 404 {"error": "not_found"}
GET  /v1/<parent>/<id>/<resource> children of a parent record (if configured)
POST /v1/<sink>                   store a JSON body (writable resources); honours Idempotency-Key
GET  /health                      unauthenticated
plus any custom ``actions`` routes (e.g. POST /v1/tasks/{id}/claim)

Request pipeline: auth (401) -> rate limit (429) -> faults (5xx / 429 / timeout /
malformed) -> latency -> route. Requests rejected by auth or the rate limiter do
not consume fault draws or scripted outcomes. Every response carries a ``Date`` header from
the API's clock, so ``Retry-After`` in HTTP-date form can be interpreted.
"""

from __future__ import annotations

import base64
import copy
import json
import math
import random
import secrets
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Any, Callable
from urllib.parse import parse_qs

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response

from ..fake_clock import Clock, RealClock, aelapse, elapse
from .config import DEFAULT_ENVELOPES, AuthConfig, FaultConfig, RateLimitConfig, ResourceConfig
from .messy import render

PAGINATION_PARAMS = {"page", "per_page", "offset", "limit", "cursor", "updated_since"}


@dataclass
class RequestLog:
    n: int
    method: str
    path: str
    params: dict[str, str]
    status: int  # 0 for a timeout
    at: float
    identity: str | None
    outcome: str  # "ok", "auth", "rate_limited", "fault:<kind>", "timeout", "client_error"


def _get(record: dict, dotted: str) -> Any:
    node: Any = record
    for key in dotted.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class MockRestAPI:
    def __init__(self, resources: list[ResourceConfig], *, auth: AuthConfig | None = None,
                 rate_limit: RateLimitConfig | None = None, faults: FaultConfig | None = None,
                 clock: Clock | None = None, base_path: str = "/v1",
                 on_request: Callable[["MockRestAPI", httpx.Request], None] | None = None,
                 actions: dict[tuple[str, str], Callable[..., tuple[int, Any]]] | None = None):
        self.resources = {r.name: r for r in resources}
        self.auth = auth if auth is not None else AuthConfig()
        self.rate_limit = rate_limit
        self.faults = faults or FaultConfig()
        self.clock = clock or RealClock()
        self.base_path = base_path.rstrip("/")
        self.on_request = on_request  # hook run before each request, e.g. to insert records mid-pagination
        # Custom routes, e.g. {("POST", "/v1/tasks/{id}/claim"): fn}. fn(api, request, params, identity)
        # returns (status, body); it runs after auth, rate limiting and faults, under the API lock.
        self.actions = [(method.upper(), [seg for seg in pattern.split("/") if seg], fn)
                        for (method, pattern), fn in (actions or {}).items()]
        self.log: list[RequestLog] = []
        self.tokens_issued = 0
        self._records = {r.name: self._sorted(r, copy.deepcopy(r.records)) for r in resources}
        self._tokens: dict[str, dict] = {}
        self._refresh: dict[str, str] = {}
        self._window: dict[str, deque] = {}
        self._attempts: dict[str, int] = {}
        self._script_hits: dict[str, int] = {}
        self._idempotency: dict[tuple[str, str], dict] = {}
        self._lock = threading.RLock()

    @classmethod
    def scale(cls, seed: int = 0, **kwargs) -> "MockRestAPI":
        """The Scale-flavoured preset: projects, annotators, tasks, submissions, reviews, results sink."""
        from .dataset import scale_resources

        sizes = kwargs.pop("sizes", {})
        kwargs.setdefault("faults", FaultConfig(seed=seed))
        return cls(scale_resources(seed, **sizes), **kwargs)

    # ------------------------------------------------------------- test helpers

    def canonical(self, resource: str) -> list[dict]:
        """Clean records in the API's default order (ground truth for tests)."""
        with self._lock:
            return copy.deepcopy(self._records[resource])

    def rendered(self, resource: str) -> list[dict]:
        """Records exactly as the API serves them (with field mess applied)."""
        cfg = self.resources[resource]
        return [self._render(cfg, r) for r in self.canonical(resource)]

    def insert(self, resource: str, record: dict) -> None:
        with self._lock:
            cfg = self.resources[resource]
            self._records[resource] = self._sorted(cfg, [*self._records[resource], copy.deepcopy(record)])

    def update(self, resource: str, record_id: Any, **changes) -> None:
        with self._lock:
            cfg = self.resources[resource]
            for record in self._records[resource]:
                if str(record[cfg.id_field]) == str(record_id):
                    record.update(changes)
                    break
            else:
                raise KeyError(record_id)
            self._records[resource] = self._sorted(cfg, self._records[resource])

    def expire_all_tokens(self) -> None:
        with self._lock:
            for info in self._tokens.values():
                info["expires_at"] = self.clock.time() - 1

    def revoke_refresh_tokens(self) -> None:
        """Invalidate every outstanding refresh token (they then answer 400 invalid_grant)."""
        with self._lock:
            self._refresh.clear()

    def requests(self, path_prefix: str = "", method: str | None = None) -> list[RequestLog]:
        return [e for e in self.log if e.path.startswith(path_prefix) and (method is None or e.method == method)]

    def client(self, base_url: str = "http://api.local", **kwargs) -> httpx.Client:
        return httpx.Client(transport=self.transport(), base_url=base_url, **kwargs)

    def async_client(self, base_url: str = "http://api.local", **kwargs) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self.transport(), base_url=base_url, **kwargs)

    # ------------------------------------------------------------- internals

    def _sorted(self, cfg: ResourceConfig, records: list[dict]) -> list[dict]:
        return sorted(records, key=lambda r: self._key(cfg, r))

    @staticmethod
    def _key(cfg: ResourceConfig, record: dict) -> list:
        return [str(_get(record, cfg.sort_field or cfg.id_field)), str(record[cfg.id_field])]

    def _render(self, cfg: ResourceConfig, record: dict) -> dict:
        return render(record, cfg.mess, seed=self.faults.seed, resource=cfg.name, record_id=record[cfg.id_field])

    def _respond(self, request: httpx.Request, status: int, body: Any, *, outcome: str, identity: str | None = None,
                 headers: dict | None = None, raw: bytes | None = None) -> httpx.Response:
        params = dict(request.url.params)
        self.log.append(RequestLog(len(self.log) + 1, request.method, request.url.path, params, status,
                                   self.clock.time(), identity, outcome))
        all_headers = {"Date": format_datetime(datetime.fromtimestamp(self.clock.time(), timezone.utc), usegmt=True),
                       **(headers or {})}
        if raw is not None:
            return httpx.Response(status, content=raw, headers={**all_headers, "Content-Type": "application/json"})
        return httpx.Response(status, json=body, headers=all_headers)

    # ---- auth

    def _token_request(self, request: httpx.Request) -> httpx.Response:
        content_type = request.headers.get("content-type", "")
        try:
            if "application/x-www-form-urlencoded" in content_type:
                body = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            else:
                body = json.loads(request.content or b"{}")
        except (ValueError, UnicodeDecodeError):
            return self._respond(request, 400, {"error": "invalid_request"}, outcome="client_error")
        grant = body.get("grant_type", "client_credentials")
        if grant == "refresh_token":
            client = self._refresh.pop(str(body.get("refresh_token")), None)
            if client is None:
                return self._respond(request, 400, {"error": "invalid_grant"}, outcome="auth")
        elif grant == "client_credentials":
            if body.get("client_id") != self.auth.client_id or body.get("client_secret") != self.auth.client_secret:
                return self._respond(request, 401, {"error": "invalid_client"}, outcome="auth")
            client = self.auth.client_id
        else:
            return self._respond(request, 400, {"error": "unsupported_grant_type"}, outcome="client_error")
        token = "tok_" + secrets.token_hex(10)
        self._tokens[token] = {"client": client, "expires_at": self.clock.time() + self.auth.token_ttl_s,
                               "requests_left": self.auth.max_requests_per_token}
        self.tokens_issued += 1
        out = {"access_token": token, "token_type": "bearer", "expires_in": self.auth.token_ttl_s}
        if self.auth.refresh_tokens:
            refresh = "rft_" + secrets.token_hex(10)
            self._refresh[refresh] = client
            out["refresh_token"] = refresh
        return self._respond(request, 200, out, outcome="ok", identity=client)

    def _authenticate(self, request: httpx.Request) -> tuple[str | None, str | None]:
        """(identity, error). Error is the 401 error code."""
        mode = self.auth.mode
        if mode == "none":
            return "anonymous", None
        if mode == "api_key":
            key = request.headers.get("x-api-key")
            if not key:
                return None, "missing_api_key"
            return (key, None) if key == self.auth.api_key else (None, "invalid_api_key")
        header = request.headers.get("authorization", "")
        if not header:
            return None, "missing_token"
        if not header.lower().startswith("bearer "):
            return None, "invalid_token"
        info = self._tokens.get(header[7:].strip())
        if info is None:
            return None, "invalid_token"
        if self.clock.time() >= info["expires_at"] or info["requests_left"] == 0:
            return None, "token_expired"
        if info["requests_left"] is not None:
            info["requests_left"] -= 1
        return info["client"], None

    # ---- rate limiting

    def _rate_limited(self, identity: str) -> tuple[float | None, dict]:
        cfg = self.rate_limit
        if cfg is None:
            return None, {}
        bucket = self._window.setdefault(identity if cfg.scope == "client" else "*", deque())
        now = self.clock.time()
        while bucket and bucket[0] <= now - cfg.window_s:
            bucket.popleft()
        wait = None
        if len(bucket) >= cfg.requests:
            wait = bucket[0] + cfg.window_s - now
        else:
            bucket.append(now)
        headers = {}
        if cfg.headers:
            reset = (bucket[0] + cfg.window_s) if bucket else now
            headers = {"X-RateLimit-Limit": str(cfg.requests),
                       "X-RateLimit-Remaining": str(max(0, cfg.requests - len(bucket))),
                       "X-RateLimit-Reset": str(math.ceil(reset))}
        return wait, headers

    def _retry_after_header(self, wait: float, fmt: str) -> dict:
        if fmt == "none":
            return {}
        if fmt == "http-date":
            at = datetime.fromtimestamp(math.ceil(self.clock.time() + wait), timezone.utc)
            return {"Retry-After": format_datetime(at, usegmt=True)}
        return {"Retry-After": str(max(1, math.ceil(wait)))}

    # ---- faults

    def _fault(self, request: httpx.Request) -> tuple[str | None, float]:
        """(fault, latency). Fault is None, "500", "429:<s>", "timeout" or "malformed"."""
        cfg = self.faults
        query = "&".join(f"{k}={v}" for k, v in sorted(request.url.params.multi_items()))
        key = f"{request.method} {request.url.path}" + (f"?{query}" if query else "")
        attempt = self._attempts.get(key, 0) + 1
        self._attempts[key] = attempt
        rng = random.Random(f"{cfg.seed}|{key}|{attempt}")
        latency = cfg.slow_latency_s if rng.random() < cfg.slow_rate else cfg.latency_s
        for needle, outcomes in cfg.scripted.items():
            if needle in key:
                hit = self._script_hits.get(needle, 0)
                self._script_hits[needle] = hit + 1
                outcome = str(outcomes[hit]) if hit < len(outcomes) else "ok"
                return (None if outcome == "ok" else outcome), latency
        if request.url.path == "/oauth/token" and not cfg.faults_on_auth:
            return None, latency
        roll_fail, roll_429, roll_bad = rng.random(), rng.random(), rng.random()
        if roll_fail < cfg.failure_rate:
            return str(rng.choice([500, 502, 503])), latency
        if roll_429 < cfg.rate_limit_rate:
            return f"429:{cfg.retry_after_s:g}", latency
        if roll_bad < cfg.malformed_rate:
            return "malformed", latency
        return None, latency

    # ---- main entry point

    def handle(self, request: httpx.Request) -> httpx.Response:
        if self.on_request is not None:
            self.on_request(self, request)
        timeout = (request.extensions.get("timeout") or {}).get("read")
        with self._lock:
            response, latency, identity = self._handle_locked(request)
        if response is None or (timeout is not None and latency > timeout):
            # A hung upstream: the client gives up after its own timeout.
            elapse(self.clock, min(latency, timeout) if timeout is not None else latency)
            with self._lock:
                self.log.append(RequestLog(len(self.log) + 1, request.method, request.url.path,
                                           dict(request.url.params), 0, self.clock.time(), identity, "timeout"))
            raise httpx.ReadTimeout("mock API did not answer in time", request=request)
        elapse(self.clock, latency)
        return response

    def _handle_locked(self, request: httpx.Request) -> tuple[httpx.Response | None, float, str | None]:
        """(response, latency, identity). A None response means the request hangs and times out."""
        path = request.url.path
        if path == "/health":
            return self._respond(request, 200, {"status": "ok"}, outcome="ok"), 0.0, None
        if path == "/oauth/token" and self.auth.mode == "oauth" and request.method == "POST":
            fault, latency = self._fault(request)
            if fault == "timeout":
                return None, max(latency, self.faults.slow_latency_s), None
            if fault:
                return self._fault_response(request, fault, None), latency, None
            return self._token_request(request), latency, None

        identity, auth_error = self._authenticate(request)
        if auth_error:
            headers = {"WWW-Authenticate": f'Bearer error="{auth_error}"'} if self.auth.mode == "oauth" else {}
            return self._respond(request, 401, {"error": auth_error}, outcome="auth", headers=headers), 0.0, None
        wait, rl_headers = self._rate_limited(identity)
        if wait is not None:
            headers = {**rl_headers, **self._retry_after_header(wait, self.rate_limit.retry_after_format)}
            return self._respond(request, 429, {"error": "rate_limited"}, outcome="rate_limited",
                                 identity=identity, headers=headers), 0.0, identity
        # Faults are drawn only for requests that got past auth and rate limiting.
        fault, latency = self._fault(request)
        if fault == "timeout":
            return None, max(latency, self.faults.slow_latency_s), identity
        if fault:
            return self._fault_response(request, fault, identity, rl_headers), latency, identity
        action = self._match_action(request)
        status, body = action(identity) if action else self._route(request)
        return self._respond(request, status, body, outcome="ok" if status < 400 else "client_error",
                             identity=identity, headers=rl_headers), latency, identity

    def _match_action(self, request: httpx.Request):
        segments = [seg for seg in request.url.path.split("/") if seg]
        for method, pattern, fn in self.actions:
            if method != request.method or len(pattern) != len(segments):
                continue
            params = {}
            for want, got in zip(pattern, segments):
                if want.startswith("{") and want.endswith("}"):
                    params[want[1:-1]] = got
                elif want != got:
                    break
            else:
                return lambda identity, fn=fn, params=params: fn(self, request, params, identity)
        return None

    def records(self, resource: str) -> list[dict]:
        """The live canonical records (no copy) for use inside actions, which run under the API lock."""
        return self._records[resource]

    def _fault_response(self, request: httpx.Request, fault: str, identity: str | None,
                        headers: dict | None = None) -> httpx.Response:
        if fault.startswith("429"):
            wait = float(fault.partition(":")[2] or self.faults.retry_after_s)
            fmt = self.rate_limit.retry_after_format if self.rate_limit else "seconds"
            return self._respond(request, 429, {"error": "rate_limited"}, outcome="fault:429", identity=identity,
                                 headers={**(headers or {}), **self._retry_after_header(wait, fmt)})
        if fault == "malformed":
            status, body = self._route(request) if identity is not None else (200, {"error": "x"})
            text = json.dumps(body)
            return self._respond(request, 200, None, outcome="fault:malformed", identity=identity,
                                 headers=headers, raw=text[: max(1, len(text) * 2 // 3)].encode())
        status = int(fault)
        return self._respond(request, status, {"error": "upstream_error"}, outcome=f"fault:{status}",
                             identity=identity, headers=headers)

    # ---- routing

    def _route(self, request: httpx.Request) -> tuple[int, Any]:
        path = request.url.path
        if not path.startswith(self.base_path + "/"):
            return 404, {"error": "not_found"}
        parts = [p for p in path[len(self.base_path):].split("/") if p]
        if len(parts) == 1 and parts[0] in self.resources:
            cfg = self.resources[parts[0]]
            if request.method == "POST" and cfg.writable:
                return self._create(cfg, request)
            if request.method == "GET":
                return self._list(cfg, request, self._records[cfg.name])
            return 405, {"error": "method_not_allowed"}
        if request.method != "GET":
            return 405, {"error": "method_not_allowed"}
        if len(parts) == 2 and parts[0] in self.resources:
            cfg = self.resources[parts[0]]
            record = next((r for r in self._records[cfg.name] if str(r[cfg.id_field]) == parts[1]), None)
            return (200, self._render(cfg, record)) if record else (404, {"error": "not_found"})
        if len(parts) == 3 and parts[2] in self.resources:
            child = self.resources[parts[2]]
            if child.parent is None or child.parent[0] != parts[0]:
                return 404, {"error": "not_found"}
            parent_cfg = self.resources[parts[0]]
            if not any(str(r[parent_cfg.id_field]) == parts[1] for r in self._records[parent_cfg.name]):
                return 404, {"error": "not_found"}
            fk = child.parent[1]
            return self._list(child, request, [r for r in self._records[child.name] if str(_get(r, fk)) == parts[1]])
        return 404, {"error": "not_found"}

    def _create(self, cfg: ResourceConfig, request: httpx.Request) -> tuple[int, Any]:
        try:
            body = json.loads(request.content or b"null")
        except ValueError:
            return 400, {"error": "invalid_json"}
        if not isinstance(body, dict):
            return 422, {"error": "body must be a JSON object"}
        key = request.headers.get("idempotency-key")
        if key and (cfg.name, key) in self._idempotency:
            return 200, self._idempotency[(cfg.name, key)]
        if cfg.validator is not None:
            problem = cfg.validator(body)
            if problem:
                return 422, {"error": problem}
        record = {**body, cfg.id_field: f"{cfg.name}_{len(self._records[cfg.name]) + 1:05d}",
                  "received_at": datetime.fromtimestamp(self.clock.time(), timezone.utc).isoformat()}
        self._records[cfg.name] = self._sorted(cfg, [*self._records[cfg.name], record])
        if key:
            self._idempotency[(cfg.name, key)] = record
        return 201, record

    def _list(self, cfg: ResourceConfig, request: httpx.Request, records: list[dict]) -> tuple[int, Any]:
        params = request.url.params
        for name, value in params.items():
            if name in cfg.filters:
                records = [r for r in records if str(_get(r, name)) == value]
        if "updated_since" in params and cfg.updated_field:
            try:
                since = _parse_time(params["updated_since"])
            except ValueError:
                return 400, {"error": "invalid_updated_since"}
            records = [r for r in records if r.get(cfg.updated_field) and _parse_time(r[cfg.updated_field]) > since]
        if cfg.pagination == "none":
            return 200, [self._render(cfg, r) for r in records]

        keys = {**DEFAULT_ENVELOPES[cfg.pagination], **cfg.envelope}
        size_param = "per_page" if cfg.pagination == "page" else "limit"
        try:
            size = int(params.get(size_param, cfg.default_page_size))
        except ValueError:
            size = -1
        if not 1 <= size <= cfg.max_page_size:
            return 400, {"error": f"{size_param} must be an integer between 1 and {cfg.max_page_size}"}

        if cfg.pagination == "page":
            try:
                page = int(params.get("page", 1))
            except ValueError:
                page = 0
            if page < 1:
                return 400, {"error": "page must be an integer >= 1"}
            chunk = records[(page - 1) * size: page * size]
            return 200, {keys["data"]: [self._render(cfg, r) for r in chunk], keys["page"]: page,
                         keys["per_page"]: size, keys["total"]: len(records),
                         keys["total_pages"]: max(1, math.ceil(len(records) / size))}
        if cfg.pagination == "offset":
            try:
                offset = int(params.get("offset", 0))
            except ValueError:
                offset = -1
            if offset < 0:
                return 400, {"error": "offset must be an integer >= 0"}
            chunk = records[offset: offset + size]
            return 200, {keys["data"]: [self._render(cfg, r) for r in chunk], keys["offset"]: offset,
                         keys["limit"]: size, keys["total"]: len(records)}
        # cursor: keyset pagination, stable under inserts
        after = None
        if params.get("cursor"):
            try:
                decoded = json.loads(base64.urlsafe_b64decode(params["cursor"] + "=" * (-len(params["cursor"]) % 4)))
                if decoded["r"] != cfg.name:
                    raise ValueError("cursor belongs to another resource")
                after = decoded["k"]
            except (ValueError, KeyError, TypeError):
                return 400, {"error": "invalid_cursor"}
        remaining = [r for r in records if after is None or self._key(cfg, r) > after]
        chunk = remaining[:size]
        next_cursor = None
        if len(remaining) > size:
            token = json.dumps({"r": cfg.name, "k": self._key(cfg, chunk[-1])})
            next_cursor = base64.urlsafe_b64encode(token.encode()).decode().rstrip("=")
        return 200, {keys["data"]: [self._render(cfg, r) for r in chunk], keys["next_cursor"]: next_cursor}

    # ------------------------------------------------------------- transports

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def app(self) -> FastAPI:
        """A real HTTP server around ``handle`` (see ``python -m shared.mock_rest``)."""
        app = FastAPI(title="Mock REST API")

        @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
        async def proxy(path: str, request: Request):
            forwarded = httpx.Request(request.method, str(request.url), headers=request.headers.raw,
                                      content=await request.body())
            try:
                response = self.handle(forwarded)
            except httpx.ReadTimeout:
                await aelapse(self.clock, self.faults.slow_latency_s)
                return Response(b'{"error": "gateway_timeout"}', status_code=504, media_type="application/json")
            headers = {k: v for k, v in response.headers.items() if k.lower() not in ("content-length", "content-type")}
            return Response(response.content, status_code=response.status_code, headers=headers,
                            media_type="application/json")

        return app
