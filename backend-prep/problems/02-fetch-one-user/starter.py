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


def get_user(client: httpx.Client, user_id: str) -> dict | None:
    raise NotImplementedError


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
