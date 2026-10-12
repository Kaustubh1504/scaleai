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

def _check(resp: httpx.Response, path: str) -> None:
    if resp.status_code == 401:
        raise AuthError(401, path, "unauthorized") 
    if not resp.is_success:
        raise ApiError(resp.status_code, path, resp.text[:200])

class CatalogClient:
    def __init__(self, http: httpx.Client, api_key: str):
        self._http = http
        self._api_key = api_key

    def __repr__(self) -> str:
        return "CatalogClient(api_key=***)"

    def get_item(self, sku: str) -> dict:
        path =f"/v1/items/{sku}"
        headers = {'X-API-Key':self._api_key}
        
        res = self._http.get(path, headers=headers)
        _check(res,path)
        return res.json()


class OrdersClient:
    TOKEN_PATH = "/oauth/token"

    def __init__(self, http: httpx.Client, client_id: str, client_secret: str):
        self._http = http
        self.client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None  # fetched lazily

    def __repr__(self) -> str:
        return f"OrdersClient(client_id={self.client_id},client_secret=***)"
    
    def _access_token(self, path)->str:
        if self._token is None:
            resp = self._http.post(self.TOKEN_PATH, data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self._client_secret,
            })
            
            if resp.status_code != 200:
                raise AuthError(resp.status_code, path, resp.text[:200])
             
            self._token = resp.json()["access_token"]
            
        return self._token

    def list_orders(self) -> list[dict]:
        path = "/v1/orders"
        resp = self._http.get(path, headers={"Authorization": f"Bearer {self._access_token(path)}"})
        _check(resp, path)
        return resp.json()["orders"]


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
