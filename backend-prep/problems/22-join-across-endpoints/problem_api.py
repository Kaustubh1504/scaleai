"""Mock Commerce API for problem 22: orders (cursor), customers (page), products (offset)."""

from __future__ import annotations

import random

from kit import MockAPI, error_response, paginate_cursor, paginate_offset, paginate_pages

MAX_ORDERS_LIMIT = 100
MAX_CUSTOMERS_PER_PAGE = 50
MAX_PRODUCTS_LIMIT = 100

TIERS = ("free", "pro", "enterprise")
FIRST = ("Acme", "Bolt", "Cora", "Dune", "Echo", "Flux", "Gale", "Hive", "Iris", "Jade")
SECOND = ("Labs", "AI", "Robotics", "Health", "Maps", "Retail")


def generate(seed: int = 7, n_customers: int = 60, n_products: int = 130, n_orders: int = 250):
    """Deterministic sample data. A few orders reference customers/products that don't exist."""
    rng = random.Random(seed)
    customers = [{"id": f"cus_{i:03d}", "name": f"{FIRST[i % 10]} {SECOND[i % 6]} {i}",
                  "tier": TIERS[rng.randrange(3)]} for i in range(1, n_customers + 1)]
    products = [{"id": f"prd_{i:03d}", "name": f"Labeling pack {i}",
                 "unit_price_cents": rng.randrange(100, 5000)} for i in range(1, n_products + 1)]
    orders = []
    for i in range(1, n_orders + 1):
        cust = "cus_404" if i % 41 == 0 else f"cus_{rng.randrange(1, n_customers + 1):03d}"
        items = [{"product_id": f"prd_{rng.randrange(1, n_products + 1):03d}", "qty": rng.randrange(1, 6)}
                 for _ in range(rng.randrange(1, 4))]
        if i % 37 == 0:
            items.append({"product_id": "prd_999", "qty": 1})
        orders.append({"id": f"ord_{i:04d}", "customer_id": cust, "items": items})
    return customers, products, orders


def _int_param(req, name, default, lo, hi):
    raw = req.params.get(name, str(default))
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if lo <= value <= hi else None


def make_api(customers=None, products=None, orders=None, *, clock=None) -> MockAPI:
    if customers is None and products is None and orders is None:
        customers, products, orders = generate()
    customers, products, orders = customers or [], products or [], orders or []
    api = MockAPI(clock=clock)
    api.customers, api.products, api.orders = customers, products, orders

    @api.route("GET", "/v1/orders")
    def list_orders(req):
        limit = _int_param(req, "limit", 20, 1, MAX_ORDERS_LIMIT)
        if limit is None:
            return error_response(400, f"limit must be 1..{MAX_ORDERS_LIMIT}")
        try:
            return paginate_cursor(orders, req.params.get("cursor") or None, limit)
        except ValueError:
            return error_response(400, "invalid cursor")

    @api.route("GET", "/v1/customers")
    def list_customers(req):
        page = _int_param(req, "page", 1, 1, 10**6)
        per_page = _int_param(req, "per_page", 20, 1, MAX_CUSTOMERS_PER_PAGE)
        if page is None or per_page is None:
            return error_response(400, f"page must be >= 1 and per_page 1..{MAX_CUSTOMERS_PER_PAGE}")
        return paginate_pages(customers, page, per_page)

    @api.route("GET", "/v1/products")
    def list_products(req):
        offset = _int_param(req, "offset", 0, 0, 10**6)
        limit = _int_param(req, "limit", 20, 1, MAX_PRODUCTS_LIMIT)
        if offset is None or limit is None:
            return error_response(400, f"offset must be >= 0 and limit 1..{MAX_PRODUCTS_LIMIT}")
        return paginate_offset(products, offset, limit)

    # Per-id lookups exist (and work), but calling them once per order is what this problem is about avoiding.
    @api.route("GET", "/v1/customers/{customer_id}")
    def get_customer(req, customer_id):
        found = next((c for c in customers if c["id"] == customer_id), None)
        return found if found else error_response(404, "no such customer")

    @api.route("GET", "/v1/products/{product_id}")
    def get_product(req, product_id):
        found = next((p for p in products if p["id"] == product_id), None)
        return found if found else error_response(404, "no such product")

    return api
