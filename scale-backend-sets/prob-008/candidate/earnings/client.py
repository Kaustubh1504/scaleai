"""Thin client for the contributor platform API (see API.md)."""

from __future__ import annotations

from typing import Any

import httpx

from mock_services.clock import Clock


class ApiError(Exception):
    """A request to the platform API failed."""

    def __init__(self, message: str, *, status: int | None = None, path: str | None = None):
        super().__init__(f"{message} (status={status}, path={path})")
        self.status = status
        self.path = path


class AuthError(ApiError):
    """The API refused our credentials."""


class EarningsClient:
    """Talks to the platform API with OAuth client credentials.

    ``http`` is an ``httpx.Client`` with ``base_url`` already set (tests pass one
    wired to the in-process mock); ``clock`` is where time comes from.
    """

    def __init__(self, http: httpx.Client, client_id: str, client_secret: str, clock: Clock):
        self.http = http
        self.client_id = client_id
        self.client_secret = client_secret
        self.clock = clock
        self._token: str | None = None

    def _get_token(self) -> str:
        if self._token is None:
            response = self.http.post("/oauth/token",
                                      json={"client_id": self.client_id, "client_secret": self.client_secret})
            if response.status_code != 200:
                raise AuthError("could not obtain a token", status=response.status_code, path="/oauth/token")
            self._token = response.json()["access_token"]
        return self._token

    def get(self, path: str, params: dict | None = None) -> Any:
        """GET a /v1 path and return the decoded JSON body."""
        response = self.http.get(path, params=params, headers={"Authorization": f"Bearer {self._get_token()}"})
        if not response.is_success:
            raise ApiError(f"unexpected response {response.text[:200]!r}", status=response.status_code, path=path)
        return response.json()

    def list_all(self, resource: str) -> list[dict]:
        """Every record of a collection, e.g. ``list_all("tasks")``."""
        body = self.get(f"/v1/{resource}")
        return body["data"]
