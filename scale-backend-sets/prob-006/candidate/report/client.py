"""Client for the Projects API (see API.md)."""

from __future__ import annotations

from typing import Any, Iterator

import httpx

from mock_services.clock import Clock


class ApiError(Exception):
    def __init__(self, message: str, *, status: int | None = None, path: str | None = None):
        super().__init__(f"{message} (status={status}, path={path})")
        self.status = status
        self.path = path


class AuthError(ApiError):
    pass


class ApiClient:
    def __init__(self, http: httpx.Client, client_id: str, client_secret: str, clock: Clock):
        self.http = http
        self.client_id = client_id
        self.client_secret = client_secret
        self.clock = clock

    def get(self, path: str, params: dict | None = None) -> Any:
        """GET a /v1 path and return the decoded JSON body."""
        raise NotImplementedError

    def iter_projects(self) -> Iterator[dict]:
        raise NotImplementedError

    def iter_project_tasks(self, project_id: str) -> Iterator[dict]:
        raise NotImplementedError
