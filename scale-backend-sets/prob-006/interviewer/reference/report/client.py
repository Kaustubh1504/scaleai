"""Client for the Projects API: bearer auth with refresh, pagination, retries."""

from __future__ import annotations

import json
import random
from email.utils import parsedate_to_datetime
from typing import Any, Iterator

import httpx

from mock_services.clock import Clock

TIMEOUT_S = 10.0
MAX_ATTEMPTS = 4
MAX_CONSECUTIVE_429 = 10
REFRESH_MARGIN_S = 5.0
PROJECTS_PER_PAGE = 10
TASKS_PER_PAGE = 25
TRANSIENT_STATUS = {500, 502, 503}


class ApiError(Exception):
    def __init__(self, message: str, *, status: int | None = None, path: str | None = None):
        super().__init__(f"{message} (status={status}, path={path})")
        self.status = status
        self.path = path


class AuthError(ApiError):
    pass


def _json_ok(response: httpx.Response) -> bool:
    try:
        response.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    return True


class ApiClient:
    def __init__(self, http: httpx.Client, client_id: str, client_secret: str, clock: Clock,
                 rng: random.Random | None = None):
        self.http = http
        self.client_id = client_id
        self.client_secret = client_secret
        self.clock = clock
        self.rng = rng or random.Random()
        self._token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at = 0.0

    # ------------------------------------------------------------- transport

    def _retry_after(self, response: httpx.Response) -> float:
        value = response.headers.get("Retry-After")
        if value is None:
            return 1.0
        try:
            return max(0.0, float(value))
        except ValueError:
            pass
        try:
            at = parsedate_to_datetime(value)
            now = parsedate_to_datetime(response.headers["Date"]) if "Date" in response.headers else None
        except (TypeError, ValueError, KeyError):
            return 1.0
        return max(0.0, (at.timestamp() - (now.timestamp() if now else self.clock.time())))

    def _backoff(self, attempt: int) -> float:
        ceiling = min(8.0, 0.5 * 2 ** (attempt - 1))
        return self.rng.uniform(ceiling / 2, ceiling)

    def _send(self, method: str, path: str, *, params: dict | None = None, json_body: dict | None = None,
              authenticated: bool = True) -> httpx.Response:
        """Send with retries for transient failures and 429s. Returns the final response."""
        failures = throttled = 0
        while True:
            headers = {}
            if authenticated:
                self._ensure_token()
                headers["Authorization"] = f"Bearer {self._token}"
            problem, status = None, None
            try:
                response = self.http.request(method, path, params=params, json=json_body, headers=headers,
                                             timeout=TIMEOUT_S)
            except httpx.TransportError as exc:
                problem = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code == 429:
                    throttled += 1
                    if throttled >= MAX_CONSECUTIVE_429:
                        raise ApiError("still rate limited after 10 attempts", status=429, path=path)
                    self.clock.sleep(self._retry_after(response))
                    continue
                status = response.status_code
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

    # ------------------------------------------------------------- auth

    def _fetch_token(self) -> None:
        issued_at = self.clock.time()
        response = None
        if self._refresh_token:
            response = self._send("POST", "/oauth/token", authenticated=False,
                                  json_body={"grant_type": "refresh_token", "refresh_token": self._refresh_token})
            self._refresh_token = None
            if response.status_code == 400:
                response = None
        if response is None:
            issued_at = self.clock.time()
            response = self._send("POST", "/oauth/token", authenticated=False,
                                  json_body={"client_id": self.client_id, "client_secret": self.client_secret})
        if response.status_code != 200:
            raise AuthError("could not obtain a token", status=response.status_code, path="/oauth/token")
        data = response.json()
        self._token = data["access_token"]
        self._refresh_token = data.get("refresh_token")
        self._expires_at = issued_at + float(data["expires_in"])

    def _ensure_token(self) -> None:
        if self._token is None or self._expires_at - self.clock.time() < REFRESH_MARGIN_S:
            self._fetch_token()

    # ------------------------------------------------------------- API

    def get(self, path: str, params: dict | None = None) -> Any:
        response = self._send("GET", path, params=params)
        if response.status_code == 401:
            self._token = None
            response = self._send("GET", path, params=params)
            if response.status_code == 401:
                raise AuthError("request rejected after refreshing the token", status=401, path=path)
        if not response.is_success:
            raise ApiError(f"unexpected response {response.text[:200]!r}", status=response.status_code, path=path)
        return response.json()

    def iter_projects(self) -> Iterator[dict]:
        page = 1
        while True:
            body = self.get("/v1/projects", {"page": page, "per_page": PROJECTS_PER_PAGE})
            yield from body["results"]
            if page >= body["total_pages"]:
                return
            page += 1

    def iter_project_tasks(self, project_id: str) -> Iterator[dict]:
        cursor = None
        while True:
            params = {"limit": TASKS_PER_PAGE, **({"cursor": cursor} if cursor else {})}
            body = self.get(f"/v1/projects/{project_id}/tasks", params)
            yield from body["data"]
            cursor = body.get("next_cursor")
            if not cursor:
                return
