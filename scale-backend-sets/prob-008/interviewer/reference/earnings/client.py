"""Client for the contributor platform API: auth, per-collection pagination, retries."""

from __future__ import annotations

import json
import random
from typing import Any

import httpx

from mock_services.clock import Clock

TIMEOUT_S = 10.0
MAX_ATTEMPTS = 4
MAX_CONSECUTIVE_429 = 10
REFRESH_MARGIN_S = 5.0
TRANSIENT_STATUS = {500, 502, 503}

# collection -> (pagination style, envelope key, largest page size the API accepts)
COLLECTIONS = {
    "annotators": ("offset", "items", 20),
    "tasks": ("cursor", "data", 100),
    "submissions": ("cursor", "data", 100),
    "reviews": ("page", "results", 50),
    "results": ("page", "results", 50),
}


class ApiError(Exception):
    """A request to the platform API failed."""

    def __init__(self, message: str, *, status: int | None = None, path: str | None = None):
        super().__init__(f"{message} (status={status}, path={path})")
        self.status = status
        self.path = path


class AuthError(ApiError):
    """The API refused our credentials."""


def _json_ok(response: httpx.Response) -> bool:
    try:
        response.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    return True


class EarningsClient:
    """Talks to the platform API with OAuth client credentials.

    ``http`` is an ``httpx.Client`` with ``base_url`` already set (tests pass one
    wired to the in-process mock); ``clock`` is where time comes from.
    """

    def __init__(self, http: httpx.Client, client_id: str, client_secret: str, clock: Clock,
                 rng: random.Random | None = None):
        self.http = http
        self.client_id = client_id
        self.client_secret = client_secret
        self.clock = clock
        self.rng = rng or random.Random()
        self._token: str | None = None
        self._expires_at = 0.0

    # ------------------------------------------------------------- transport

    def _retry_after(self, response: httpx.Response) -> float:
        try:
            return max(0.0, float(response.headers["Retry-After"]))
        except (KeyError, ValueError):
            return 1.0

    def _backoff(self, failures: int) -> float:
        ceiling = min(8.0, 0.5 * 2 ** (failures - 1))
        return self.rng.uniform(ceiling / 2, ceiling)

    def _send(self, method: str, path: str, *, params: dict | None = None, json_body: dict | None = None,
              headers: dict | None = None, authenticated: bool = True) -> httpx.Response:
        """One logical request: retries transient failures and 429s, returns the final response."""
        failures = throttled = 0
        while True:
            all_headers = dict(headers or {})
            if authenticated:
                all_headers["Authorization"] = f"Bearer {self._ensure_token()}"
            problem, status = None, None
            try:
                response = self.http.request(method, path, params=params, json=json_body, headers=all_headers,
                                             timeout=TIMEOUT_S)
            except httpx.TransportError as exc:
                problem = f"{type(exc).__name__}: {exc}"
            else:
                status = response.status_code
                if status == 429:
                    throttled += 1
                    if throttled >= MAX_CONSECUTIVE_429:
                        raise ApiError(f"still rate limited after {throttled} attempts", status=429, path=path)
                    self.clock.sleep(self._retry_after(response))
                    continue
                if status in TRANSIENT_STATUS:
                    problem = f"HTTP {status}"
                elif response.is_success and not _json_ok(response):
                    problem = "malformed JSON body"
                else:
                    return response
            throttled = 0
            failures += 1
            if failures >= MAX_ATTEMPTS:
                raise ApiError(f"giving up after {MAX_ATTEMPTS} attempts: {problem}", status=status, path=path)
            self.clock.sleep(self._backoff(failures))

    def _ensure_token(self) -> str:
        if self._token is None or self._expires_at - self.clock.time() < REFRESH_MARGIN_S:
            issued_at = self.clock.time()
            response = self._send("POST", "/oauth/token", authenticated=False,
                                  json_body={"client_id": self.client_id, "client_secret": self.client_secret})
            if response.status_code != 200:
                raise AuthError("could not obtain a token", status=response.status_code, path="/oauth/token")
            data = response.json()
            self._token, self._expires_at = data["access_token"], issued_at + float(data["expires_in"])
        return self._token

    def _checked(self, response: httpx.Response, path: str) -> Any:
        if not response.is_success:
            raise ApiError(f"unexpected response {response.text[:200]!r}", status=response.status_code, path=path)
        return response.json()

    # ------------------------------------------------------------- API

    def get(self, path: str, params: dict | None = None) -> Any:
        """GET a /v1 path and return the decoded JSON body."""
        return self._checked(self._send("GET", path, params=params), path)

    def post(self, path: str, body: dict, *, idempotency_key: str | None = None) -> Any:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
        return self._checked(self._send("POST", path, json_body=body, headers=headers), path)

    def list_all(self, resource: str) -> list[dict]:
        """Every record of a collection, following that collection's pagination style."""
        style, key, size = COLLECTIONS[resource]
        path, out = f"/v1/{resource}", []
        if style == "cursor":
            cursor = None
            while True:
                body = self.get(path, {"limit": size, **({"cursor": cursor} if cursor else {})})
                out.extend(body[key])
                cursor = body.get("next_cursor")
                if not cursor:
                    return out
        if style == "offset":
            while True:
                body = self.get(path, {"offset": len(out), "limit": size})
                out.extend(body[key])
                if not body[key] or len(out) >= body["total"]:
                    return out
        page = 1
        while True:
            body = self.get(path, {"page": page, "per_page": size})
            out.extend(body[key])
            if page >= body["total_pages"]:
                return out
            page += 1
