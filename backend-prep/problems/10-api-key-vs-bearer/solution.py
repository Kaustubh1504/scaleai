"""10. API key vs OAuth bearer token: reference solution."""

from __future__ import annotations

import httpx


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


class AuthError(ApiError):
    pass


def _check(resp: httpx.Response, path: str) -> None:
    if resp.status_code == 401:
        raise AuthError(401, path, "unauthorized")  # don't echo a body that may quote credentials
    if not resp.is_success:
        raise ApiError(resp.status_code, path, resp.text)


# No custom __repr__: the default object repr never shows the secrets.
class CatalogClient:
    def __init__(self, http: httpx.Client, api_key: str):
        self.http = http
        self.api_key = api_key

    def get_item(self, sku: str) -> dict:
        resp = self.http.get(f"/v1/items/{sku}", headers={"X-API-Key": self.api_key})
        _check(resp, f"/v1/items/{sku}")
        return resp.json()


class OrdersClient:
    def __init__(self, http: httpx.Client, client_id: str, client_secret: str):
        self.http = http
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None

    def list_orders(self) -> list[dict]:
        if self.token is None:
            resp = self.http.post("/oauth/token", data={"grant_type": "client_credentials",
                                                        "client_id": self.client_id,
                                                        "client_secret": self.client_secret})
            if resp.status_code != 200:
                raise AuthError(resp.status_code, "/oauth/token", "token request rejected")
            self.token = resp.json()["access_token"]
        resp = self.http.get("/v1/orders", headers={"Authorization": f"Bearer {self.token}"})
        _check(resp, "/v1/orders")
        return resp.json()["orders"]


if __name__ == "__main__":
    from problem_api import API_KEY, CLIENT_ID, CLIENT_SECRET, make_api

    api = make_api()
    http = api.client()
    catalog = CatalogClient(http, API_KEY)
    for o in OrdersClient(http, CLIENT_ID, CLIENT_SECRET).list_orders():
        print(o["id"], o["customer"], o["qty"] * catalog.get_item(o["sku"])["price_cents"])
    print([c.key for c in api.log])
