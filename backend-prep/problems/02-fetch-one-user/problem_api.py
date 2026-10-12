"""Mock Users API for problem 02. Tests and your __main__ block both use make_api()."""

from __future__ import annotations

import httpx

from kit import BASE_URL, MockAPI, error_response

USERS = {
    "u_001": {"id": "u_001", "email": "ada@labelco.test", "role": "annotator", "active": True},
    "u_002": {"id": "u_002", "email": "grace@labelco.test", "role": "reviewer", "active": True},
    "u_003": {"id": "u_003", "email": "linus@labelco.test", "role": "annotator", "active": False},
    "ops-admin": {"id": "ops-admin", "email": "ops@labelco.test", "role": "admin", "active": True},
}


def make_api(clock=None) -> MockAPI:
    api = MockAPI(clock=clock)
    api.users = USERS

    @api.route("GET", "/v1/users/{user_id}")
    def get_user(req, user_id):
        user = USERS.get(user_id)
        if user is None:
            return error_response(404, f"user {user_id!r} not found")
        return dict(user)

    @api.route("GET", "/v1/admin")
    def admin(req):
        return {"secret": "you should never be able to reach this through get_user"}

    return api


class _Recording(httpx.BaseTransport):
    """Wraps the mock transport and remembers each request's timeout settings."""

    def __init__(self, inner: httpx.BaseTransport, timeouts: list[dict]):
        self.inner = inner
        self.timeouts = timeouts

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.timeouts.append(dict(request.extensions.get("timeout", {})))
        return self.inner.handle_request(request)


def recording_client(api: MockAPI) -> httpx.Client:
    """A client whose default timeout is 30 s; per-request timeouts land in ``api.timeouts``."""
    api.timeouts = []
    return httpx.Client(base_url=BASE_URL, timeout=30.0, transport=_Recording(api.transport(), api.timeouts))
