"""22. Joining three paginated endpoints: reference solution."""

from __future__ import annotations

from collections import Counter, defaultdict

import httpx


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


def _get(client: httpx.Client, path: str, params: dict) -> dict:
    resp = client.get(path, params=params)
    if not resp.is_success:
        raise ApiError(resp.status_code, path, resp.text)
    return resp.json()


def build_report(client: httpx.Client) -> dict:
    customers = {}
    page = pages = 1
    while page <= pages:
        body = _get(client, "/v1/customers", {"page": page, "per_page": 50})
        customers.update({c["id"]: c for c in body["data"]})
        pages = body["total_pages"]
        page += 1

    prices = {}
    offset, total = 0, 1
    while offset < total:
        body = _get(client, "/v1/products", {"offset": offset, "limit": 100})
        prices.update({p["id"]: p["unit_price_cents"] for p in body["items"]})
        offset, total = offset + len(body["items"]), body["total"]

    orders = []
    params = {"limit": 100}
    while True:
        body = _get(client, "/v1/orders", params)
        orders += body["results"]
        if not body.get("next_cursor"):
            break
        params = {"limit": 100, "cursor": body["next_cursor"]}

    order_count: Counter[str] = Counter()
    revenue: Counter[str] = Counter()
    qtys: dict[str, Counter[str]] = defaultdict(Counter)
    orphans = []
    for order in orders:
        cid = order["customer_id"]
        pids = [it["product_id"] for it in order["items"]]
        unknown = next((p for p in pids if p not in prices), None)
        if cid not in customers:
            orphans.append({"order_id": order["id"], "reason": "unknown_customer", "ref": cid})
        elif unknown is not None:
            orphans.append({"order_id": order["id"], "reason": "unknown_product", "ref": unknown})
        else:
            order_count[cid] += 1
            for it in order["items"]:
                revenue[cid] += it["qty"] * prices[it["product_id"]]
                qtys[cid][it["product_id"]] += it["qty"]

    rows = [{"customer_id": cid, "name": c["name"], "tier": c["tier"], "orders": order_count[cid],
             "total_cents": revenue[cid],
             "top_product": min(qtys[cid], key=lambda p: (-qtys[cid][p], p), default=None)}
            for cid, c in sorted(customers.items())]
    return {"customers": rows, "orphans": sorted(orphans, key=lambda o: o["order_id"])}


if __name__ == "__main__":
    from problem_api import make_api

    api = make_api()
    report = build_report(api.client())
    for row in report["customers"][:5]:
        print(row)
    print("orphans:", report["orphans"])
    print(len(api.log), "requests")
