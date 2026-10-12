"""07. Page-number pagination: reference solution."""

from __future__ import annotations

from itertools import count

import httpx


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


def fetch_all_products(client: httpx.Client, api_key: str, per_page: int = 20) -> list[dict]:
    products = []
    for page in count(1):
        resp = client.get("/v1/products", params={"page": page, "per_page": per_page},
                          headers={"X-API-Key": api_key})
        if not resp.is_success:
            raise ApiError(resp.status_code, "/v1/products", resp.text)
        body = resp.json()
        products.extend(body["data"])
        if not body["data"] or page >= body["total_pages"]:
            return products


if __name__ == "__main__":
    from problem_api import API_KEY, make_api

    api = make_api(n_products=47)
    products = fetch_all_products(api.client(), API_KEY, per_page=20)
    print(len(products), "products; pages:", [c.params["page"] for c in api.log])
