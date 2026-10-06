"""Client for the Tasks API: API-key auth, cursor pagination, retries, rate limits."""

from __future__ import annotations

import json
import random
from email.utils import parsedate_to_datetime
from typing import Any, Iterator

import httpx

from mock_services.clock import Clock

MAX_ATTEMPTS = 5
MAX_CONSECUTIVE_429 = 8
TASKS_PER_PAGE = 25


class ApiError(Exception):
    def __init__(self, message: str, *, status: int | None = None, path: str | None = None):
        super().__init__(f"{message} (status={status}, path={path})")
        self.status = status
        self.path = path


class AuthError(ApiError):
    pass


class NotFoundError(ApiError):
    pass


class RetriesExhausted(ApiError):
    """A transient failure (or a 429) persisted past the retry budget."""


def _header_float(response: httpx.Response, name: str) -> float | None:
    try:
        return float(response.headers[name])
    except (KeyError, ValueError):
        return None


class TasksClient:
    def __init__(self, http: httpx.Client, api_key: str, clock: Clock, rng: random.Random | None = None):
        self.http = http
        self.api_key = api_key
        self.clock = clock
        self.rng = rng or random.Random()
        self._resume_at: float | None = None  # X-RateLimit-Reset after the quota hit 0

    # ------------------------------------------------------------- rate limits

    def _note_rate_limit(self, response: httpx.Response) -> None:
        remaining = _header_float(response, "X-RateLimit-Remaining")
        if remaining is not None:
            self._resume_at = _header_float(response, "X-RateLimit-Reset") if remaining <= 0 else None

    def _throttle(self) -> None:
        if self._resume_at is not None:
            wait = self._resume_at - self.clock.time()
            self._resume_at = None
            if wait > 0:
                self.clock.sleep(wait)

    def _retry_after(self, response: httpx.Response) -> float:
        value = response.headers.get("Retry-After")
        if value is not None:
            try:
                return max(0.0, float(value))
            except ValueError:
                pass
            try:  # HTTP-date: compare against the server's Date header, not our clock
                at = parsedate_to_datetime(value).timestamp()
                now = parsedate_to_datetime(response.headers["Date"]).timestamp()
                return max(0.0, at - now)
            except (TypeError, ValueError, KeyError):
                pass
        reset = _header_float(response, "X-RateLimit-Reset")
        return max(0.0, reset - self.clock.time()) if reset is not None else 1.0

    def _backoff(self, failures: int) -> float:
        return 2 ** (failures - 1) + self.rng.uniform(0, 1)

    # ------------------------------------------------------------- requests

    def get(self, path: str, params: dict | None = None) -> Any:
        """GET with retries. Returns the decoded body or raises an ApiError subclass."""
        failures = throttled = 0
        while True:
            self._throttle()
            status = None
            try:
                response = self.http.get(path, params=params, headers={"X-API-Key": self.api_key})
            except httpx.TransportError as exc:
                problem = f"{type(exc).__name__}: {exc}"
            else:
                self._note_rate_limit(response)
                status = response.status_code
                if status == 429:
                    throttled += 1
                    if throttled >= MAX_CONSECUTIVE_429:
                        raise RetriesExhausted(f"still rate limited after {throttled} tries", status=429, path=path)
                    self.clock.sleep(self._retry_after(response))
                    continue
                if response.is_success:
                    try:
                        return response.json()
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        problem = "truncated JSON body"
                elif status >= 500:
                    problem = f"HTTP {status}"
                elif status == 401:
                    raise AuthError("API key rejected", status=status, path=path)
                elif status == 404:
                    raise NotFoundError("not found", status=status, path=path)
                else:
                    raise ApiError(f"unexpected response {response.text[:200]!r}", status=status, path=path)
            throttled = 0
            failures += 1
            if failures >= MAX_ATTEMPTS:
                raise RetriesExhausted(f"giving up after {failures} attempts: {problem}", status=status, path=path)
            self.clock.sleep(self._backoff(failures))

    def iter_task_pages(self, project_id: str) -> Iterator[list[dict]]:
        cursor = None
        while True:
            params = {"limit": TASKS_PER_PAGE, **({"cursor": cursor} if cursor else {})}
            body = self.get(f"/v1/projects/{project_id}/tasks", params)
            yield body["data"]
            cursor = body.get("next_cursor")
            if not cursor:
                return
