"""02. Fetch one user safely

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import re
import httpx


class UserApiError(Exception):
    def __init__(self, status: int | None, path: str, message: str = ""):
        super().__init__(f"{status if status is not None else 'no response'} on {path}: {message}")
        self.status = status
        self.path = path


TIMEOUT_S = 5

user_id_regex =re.compile(r"[a-zA-Z0-9_-]{1,64}")

def get_user(client: httpx.Client, user_id: str) -> dict | None:
    if not isinstance(user_id,str) or not user_id_regex.fullmatch(user_id):
        raise ValueError("user_id should be alpha numeric and contain only - and _")
    path = f"/v1/users/{user_id}"
    try:
        resp = client.get(path, timeout=TIMEOUT_S)
    except httpx.TransportError as exc:
        raise UserApiError(None, path, f"{type(exc).__name__}: {exc}") from exc

    if resp.status_code == 404:
        return None
    if not resp.is_success:
        raise UserApiError(resp.status_code, path, resp.text[:200])
        
    return resp.json()
    


if __name__ == "__main__":
    from problem_api import make_api, recording_client

    api = make_api()
    client = recording_client(api)
    print(get_user(client, "u_001"))
    print(get_user(client, "u_404"))
    for bad in ["../admin", ""]:
        try:
            get_user(client, bad)
        except ValueError as exc:
            print("rejected:", exc)
    api.script("GET /v1/users/u_002", ["timeout"])
    try:
        get_user(client, "u_002")
    except UserApiError as exc:
        print("UserApiError:", exc, "| cause:", type(exc.__cause__).__name__)
    print("timeouts sent:", api.timeouts)
