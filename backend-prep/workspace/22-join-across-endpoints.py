"""22. Joining three paginated endpoints

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from collections import Counter
from typing import Iterator
import httpx


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path
        
def _get(client: httpx.Client, path: str, params: dict) -> dict:
    resp = client.get(path, params=params)
    if not resp.is_success:
        raise ApiError(resp.status_code, path, resp.text[:200])
    return resp.json()

def iter_orders(client: httpx.Client) -> Iterator[dict]:
    cursor = None
    while True:
        params = {"limit":100}
        if cursor:
            params["cursor"] = cursor
        
        body = _get(client, "/v1/orders", params)
        yield from body["results"]
        cursor = body.get("next_cursor")
        if not cursor:
            return
        

def iter_customers(client: httpx.Client) -> Iterator[dict]:
    page = 1
    while True:
        body = _get(client, "/v1/customers", {"page":page, "per_page":50})
        yield from body["data"]
        if page>=body["total_pages"]:
            return
        page+=1


def iter_products(client: httpx.Client) -> Iterator[dict]:
    offset = 0
    while True:
        body = _get(client, "/v1/products", {"offset": offset, "limit": 100})
        yield from body["items"]
        offset += len(body["items"])
        if not body["items"] or offset >= body["total"]:
            return


def build_report(client: httpx.Client) -> dict:
    customers = {c["id"]:c for c in iter_customers(client)}
    prices = {p["id"]: p["unit_price_cents"] for p in iter_products(client)}
    
    order_count = Counter()
    revenue = Counter()
    qty_by_product = {cid: Counter() for cid in customers}
    orphans = []
    
    for order in iter_orders(client):
        cid = order["customer_id"]
        if cid not in customers:
            orphans.append({"order_id": order["id"], "reason": "unknown_customer", "ref": cid})
            continue
        
        missing = next(
            (
                it["product_id"] for it in order["items"] 
                 if it["product_id"] not in prices
            ),None)
        
        if missing is not None:
            orphans.append({"order_id": order["id"], "reason": "unknown_product", "ref": missing})
            continue
            
        order_count[cid]+=1
        for it in order["items"]:
            revenue[cid]+=it["qty"]*prices[it["product_id"]]
            qty_by_product[cid][it["product_id"]]+=it["qty"]
        
        
    rows = []
    for cid in sorted(customers):
        c = customers[cid]
        qtys = qty_by_product[cid]
        top = min(qtys, key=lambda pid: (-qtys[pid], pid)) if qtys else None
        rows.append({"customer_id": cid, "name": c["name"], "tier": c["tier"], "orders": order_count[cid],
                     "total_cents": revenue[cid], "top_product": top})
    return {"customers": rows, "orphans": sorted(orphans, key=lambda o: o["order_id"])}
        



if __name__ == "__main__":
    from problem_api import make_api

    api = make_api()
    report = build_report(api.client())
    for row in report["customers"][:5]:
        print(row)
    print("...", len(report["customers"]), "customers")
    for o in report["orphans"]:
        print("orphan:", o)
    print(len(api.log), "requests:", sorted({c.path for c in api.log}))
