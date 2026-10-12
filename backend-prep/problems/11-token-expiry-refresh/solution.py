"""11. Token expiry and refresh: reference solution."""

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
    def __init__(self, http: httpx.Client, client_id: str, client_secret: str, clock):
        self.http = http
        self.client_id = client_id
        self.client_secret = client_secret
        self.clock = clock
        self.token = None
        self.refresh_token = None
        self.expires_at = 0.0

    def _renew(self) -> None:
        grants = [{"grant_type": "client_credentials"}]
        if self.refresh_token:
            grants.insert(0, {"grant_type": "refresh_token", "refresh_token": self.refresh_token})
        for grant in grants:
            started = self.clock.time()  # before the request, so we err on expiring early
            resp = self.http.post("/oauth/token", data={**grant, "client_id": self.client_id,
                                                        "client_secret": self.client_secret})
            if resp.status_code == 200:
                body = resp.json()
                self.token, self.refresh_token = body["access_token"], body.get("refresh_token")
                self.expires_at = started + body["expires_in"]
                return
            if resp.status_code != 400 or grant["grant_type"] == "client_credentials":
                raise AuthError(resp.status_code, "/oauth/token", "token request rejected")

    def _send(self, path: str, params: dict | None) -> httpx.Response:
        return self.http.get(path, params=params, headers={"Authorization": f"Bearer {self.token}"})

    def get(self, path: str, params: dict | None = None) -> dict:
        if self.token is None or self.expires_at - self.clock.time() < 2:
            self._renew()
        resp = self._send(path, params)
        if resp.status_code == 401:
            self._renew()
            resp = self._send(path, params)
            if resp.status_code == 401:
                raise AuthError(401, path, "still unauthorized after a fresh token")
        if not resp.is_success:
            raise ApiError(resp.status_code, path, resp.text)
        return resp.json()


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
    print(len(api.calls("POST", "/oauth/token")), "token requests;",
          sum(c.status == 401 for c in api.log), "401s")
