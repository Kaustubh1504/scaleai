"""11. Token expiry and refresh

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import httpx


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


class AuthError(ApiError):
    pass


class ApiClient:
    TOKEN_PATH = "/oauth/token"
    REFRESH_MARGIN_S = 2.0

    def __init__(self, http: httpx.Client, client_id: str, client_secret: str, clock):
        self._http = http
        self._client_id = client_id
        self._client_secret = client_secret
        self._clock = clock
        self._token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at = 0.0

    def __repr__(self) -> str:
        return f"ApiClient(client_id={self._client_id!r})"

    def get(self, path: str, params: dict | None = None) -> dict:
        raise NotImplementedError


if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import CLIENT_ID, CLIENT_SECRET, make_api

    clock = FakeClock(start=0)
    api = make_api(clock)
    client = ApiClient(api.client(), CLIENT_ID, CLIENT_SECRET, clock)
    for i in range(1, 61):
        if i == 30:
            api.issuer.revoke_all()
        client.get(f"/v1/tasks/task_{i:04d}")
    tokens = api.calls("POST", "/oauth/token")
    print(f"60 tasks by t={clock.time():.0f}; {len(tokens)} token requests;",
          sum(c.status == 401 for c in api.log), "401s")
