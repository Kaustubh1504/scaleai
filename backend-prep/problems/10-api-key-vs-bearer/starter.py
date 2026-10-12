"""10. API key vs OAuth bearer token

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


class CatalogClient:
    def __init__(self, http: httpx.Client, api_key: str):
        self._http = http
        self._api_key = api_key

    def __repr__(self) -> str:
        raise NotImplementedError

    def get_item(self, sku: str) -> dict:
        raise NotImplementedError


class OrdersClient:
    TOKEN_PATH = "/oauth/token"

    def __init__(self, http: httpx.Client, client_id: str, client_secret: str):
        self._http = http
        self.client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None  # fetched lazily

    def __repr__(self) -> str:
        raise NotImplementedError

    def list_orders(self) -> list[dict]:
        raise NotImplementedError


if __name__ == "__main__":
    from problem_api import API_KEY, CLIENT_ID, CLIENT_SECRET, make_api

    api = make_api()
    http = api.client()
    orders = OrdersClient(http, CLIENT_ID, CLIENT_SECRET)
    catalog = CatalogClient(http, API_KEY)
    for o in orders.list_orders():
        item = catalog.get_item(o["sku"])
        print(o["id"], o["customer"], o["qty"] * item["price_cents"])
    print(orders, catalog, "|", [c.key for c in api.log])
