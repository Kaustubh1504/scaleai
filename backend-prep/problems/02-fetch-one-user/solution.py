"""02. Fetch one user safely: reference solution."""

from __future__ import annotations

import re

import httpx


class UserApiError(Exception):
    def __init__(self, status: int | None, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


def get_user(client: httpx.Client, user_id: str) -> dict | None:
    if not isinstance(user_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", user_id):
        raise ValueError(f"invalid user id: {user_id!r}")
    path = f"/v1/users/{user_id}"
    try:
        resp = client.get(path, timeout=5)
    except httpx.TransportError as exc:
        raise UserApiError(None, path, str(exc)) from exc
    if resp.status_code == 404:
        return None
    if not resp.is_success:
        raise UserApiError(resp.status_code, path, resp.text[:200])
    return resp.json()


if __name__ == "__main__":
    from problem_api import make_api, recording_client

    api = make_api()
    client = recording_client(api)
    print(get_user(client, "u_001"), get_user(client, "u_404"))
    api.script("GET /v1/users/u_002", ["timeout"])
    try:
        get_user(client, "u_002")
    except UserApiError as exc:
        print("UserApiError:", exc, "| cause:", type(exc.__cause__).__name__)
