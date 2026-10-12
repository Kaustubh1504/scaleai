"""07. Page-number pagination

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import httpx


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


def fetch_all_products(client: httpx.Client, api_key: str, per_page: int = 20) -> list[dict]:
        params = {'page':1, "per_page": per_page}
        headers = {"X-API-Key":api_key}
        body = []
        path = "/v1/products"
        while True:
            res = client.get(path, params=params,headers=headers)
            if not res.is_success:
                raise ApiError(res.status_code, path, res.text[:200])
            data = res.json()['data']
            if data and len(data)>0:
                body.extend(res.json()['data'])
            else:
                return body
            if params['page']>=int(res.json()['total_pages']):
                return body
            params['page']+=1

        return []


if __name__ == "__main__":
    from problem_api import API_KEY, make_api

    api = make_api(n_products=47)
    products = fetch_all_products(api.client(), API_KEY, per_page=20)
    print(len(products), "products in", len(api.log), "requests:", [c.params["page"] for c in api.log])
