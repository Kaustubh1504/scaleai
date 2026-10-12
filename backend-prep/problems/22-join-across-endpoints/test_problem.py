from collections import Counter

import pytest

from problem_api import make_api

CUSTOMERS = [
    {"id": "cus_b", "name": "Bolt Robotics", "tier": "free"},
    {"id": "cus_a", "name": "Acme Labs", "tier": "pro"},
    {"id": "cus_c", "name": "Cora Health", "tier": "enterprise"},
]
PRODUCTS = [
    {"id": "p1", "name": "Image boxes", "unit_price_cents": 250},
    {"id": "p2", "name": "RLHF pairs", "unit_price_cents": 1000},
    {"id": "p3", "name": "OCR pages", "unit_price_cents": 99},
]
ORDERS = [
    {"id": "o1", "customer_id": "cus_b", "items": [{"product_id": "p1", "qty": 4}, {"product_id": "p2", "qty": 1}]},
    {"id": "o2", "customer_id": "cus_a", "items": [{"product_id": "p2", "qty": 2}]},
    {"id": "o6", "customer_id": "cus_zz", "items": [{"product_id": "p9", "qty": 1}]},
    {"id": "o3", "customer_id": "cus_a", "items": [{"product_id": "p3", "qty": 3}, {"product_id": "p1", "qty": 1}]},
    {"id": "o4", "customer_id": "cus_x", "items": [{"product_id": "p1", "qty": 1}]},
    {"id": "o5", "customer_id": "cus_a", "items": [{"product_id": "p1", "qty": 1}, {"product_id": "p9", "qty": 2},
                                                   {"product_id": "p8", "qty": 1}]},
]


def small_api():
    return make_api(CUSTOMERS, PRODUCTS, ORDERS)


def expected_report(api):
    """Ground truth for the generated dataset, computed straight from the mock's data."""
    customers = {c["id"]: c for c in api.customers}
    prices = {p["id"]: p["unit_price_cents"] for p in api.products}
    stats = {cid: {"orders": 0, "total": 0, "qty": Counter()} for cid in customers}
    orphans = []
    for o in api.orders:
        if o["customer_id"] not in customers:
            orphans.append({"order_id": o["id"], "reason": "unknown_customer", "ref": o["customer_id"]})
            continue
        bad = [it["product_id"] for it in o["items"] if it["product_id"] not in prices]
        if bad:
            orphans.append({"order_id": o["id"], "reason": "unknown_product", "ref": bad[0]})
            continue
        s = stats[o["customer_id"]]
        s["orders"] += 1
        for it in o["items"]:
            s["total"] += it["qty"] * prices[it["product_id"]]
            s["qty"][it["product_id"]] += it["qty"]
    rows = []
    for cid in sorted(customers):
        s = stats[cid]
        top = sorted(s["qty"].items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if s["qty"] else None
        rows.append({"customer_id": cid, "name": customers[cid]["name"], "tier": customers[cid]["tier"],
                     "orders": s["orders"], "total_cents": s["total"], "top_product": top})
    return {"customers": rows, "orphans": sorted(orphans, key=lambda o: o["order_id"])}


def test_small_report_customers(sol):
    """Per-customer rows: orders, total_cents, top_product by qty, sorted by customer_id"""
    rows = sol.build_report(small_api().client())["customers"]
    assert rows == [
        {"customer_id": "cus_a", "name": "Acme Labs", "tier": "pro", "orders": 2, "total_cents": 2547,
         "top_product": "p3"},
        {"customer_id": "cus_b", "name": "Bolt Robotics", "tier": "free", "orders": 1, "total_cents": 2000,
         "top_product": "p1"},
        {"customer_id": "cus_c", "name": "Cora Health", "tier": "enterprise", "orders": 0, "total_cents": 0,
         "top_product": None},
    ], "cus_a's top product is p3 (qty 3) even though p2 earned more: top_product is by quantity"


def test_small_report_orphans(sol):
    """Orphans: unknown customer checked first, else first unknown product; sorted by order_id"""
    orphans = sol.build_report(small_api().client())["orphans"]
    assert orphans == [
        {"order_id": "o4", "reason": "unknown_customer", "ref": "cus_x"},
        {"order_id": "o5", "reason": "unknown_product", "ref": "p9"},
        {"order_id": "o6", "reason": "unknown_customer", "ref": "cus_zz"},
    ]


def test_top_product_tie(sol):
    """top_product ties on qty go to the smaller product_id"""
    orders = [{"id": "o1", "customer_id": "cus_a", "items": [{"product_id": "p3", "qty": 2}]},
              {"id": "o2", "customer_id": "cus_a", "items": [{"product_id": "p2", "qty": 1}, {"product_id": "p3", "qty": 0},
                                                             {"product_id": "p2", "qty": 1}]}]
    rows = sol.build_report(make_api(CUSTOMERS, PRODUCTS, orders).client())["customers"]
    assert rows[0]["top_product"] == "p2", "p2 and p3 both have qty 2: p2 wins on id"
    assert rows[0]["total_cents"] == 2 * 99 + 2 * 1000


def test_no_orders(sol):
    """With no orders at all, every customer is listed with zeros and no orphans"""
    report = sol.build_report(make_api(CUSTOMERS, PRODUCTS, []).client())
    assert [r["customer_id"] for r in report["customers"]] == ["cus_a", "cus_b", "cus_c"]
    assert all(r["orders"] == 0 and r["total_cents"] == 0 and r["top_product"] is None for r in report["customers"])
    assert report["orphans"] == []


def test_full_dataset_matches(sol):
    """Generated dataset (60 customers, 130 products, 250 orders): report matches ground truth"""
    api = make_api()
    report = sol.build_report(api.client())
    expected = expected_report(api)
    assert len(report["customers"]) == 60, "every customer must appear (did you read every page?)"
    assert report["orphans"] == expected["orphans"]
    assert report["customers"] == expected["customers"]


def test_each_collection_paginated_fully(sol):
    """All three list endpoints are paginated to the end (more than one page each)"""
    api = make_api()
    sol.build_report(api.client())
    for path in ("/v1/orders", "/v1/customers", "/v1/products"):
        assert len(api.calls("GET", path)) >= 2, f"{path} has more than one page at max page size"
    assert all(c.status == 200 for c in api.log), "every request should succeed (check page-size limits)"


def test_no_per_record_requests(sol):
    """Never calls per-id endpoints, never repeats a page, uses max page sizes (about 7 requests)"""
    api = make_api()
    sol.build_report(api.client())
    per_id = [c.path for c in api.log if c.path.count("/") > 2]
    assert per_id == [], f"made per-record requests, e.g. {per_id[:3]}"
    seen = [(c.path, tuple(sorted(c.params.items()))) for c in api.log]
    assert len(seen) == len(set(seen)), "a page was requested more than once"
    assert len(api.log) <= 10, f"{len(api.log)} requests: at max page size three crawls need about 7"


def test_api_error(sol):
    """A 503 while paging products raises ApiError(503, "/v1/products")"""
    api = make_api()
    api.script("GET /v1/products", ["pass", 503])
    with pytest.raises(sol.ApiError) as exc:
        sol.build_report(api.client())
    assert exc.value.status == 503
    assert exc.value.path == "/v1/products"
