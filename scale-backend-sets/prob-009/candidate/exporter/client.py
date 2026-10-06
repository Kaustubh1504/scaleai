"""Client for the Tasks API (see API.md)."""

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


class TasksClient:
    def __init__(self, http: httpx.Client, api_key: str, clock: Clock):
        self.http = http
        self.api_key = api_key
        self.clock = clock

    def get(self, path: str, params: dict | None = None) -> Any:
        """GET a /v1 path and return the decoded JSON body."""
        raise NotImplementedError

    def iter_task_pages(self, project_id: str) -> Iterator[list[dict]]:
        """Yield each page of a project's tasks (a list of records, as received)."""
        raise NotImplementedError
