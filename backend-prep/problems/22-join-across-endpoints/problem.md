# 22. Joining three paginated endpoints

Account managers want a per-customer report: how many labeling orders each
customer placed, how much they spent, and what they buy most. The data lives
in three services, each paginated in its own way. Orders store only
`customer_id` and `product_id`s, so you have to join. Some orders point at
customers or products that were deleted; those must be reported, not crash
the job. And with thousands of orders, a request per order is not an option.

## The API

No auth. Every list endpoint returns **400** for an out-of-range size.

| endpoint | params | response |
|----------|--------|----------|
| `GET /v1/orders` | `limit` 1..100, `cursor` (omit on the first call) | `{"results": [...], "next_cursor": "..." \| null}` |
| `GET /v1/customers` | `page` ≥ 1, `per_page` 1..50 | `{"data": [...], "page", "per_page", "total", "total_pages"}` |
| `GET /v1/products` | `offset` ≥ 0, `limit` 1..100 | `{"items": [...], "offset", "limit", "total"}` |
| `GET /v1/customers/{id}`, `GET /v1/products/{id}` | | one record (exists, but **don't** use it) |

```json
order:    {"id": "ord_0001", "customer_id": "cus_017", "items": [{"product_id": "prd_042", "qty": 3}]}
customer: {"id": "cus_017", "name": "Hive Health 17", "tier": "pro"}
product:  {"id": "prd_042", "name": "Labeling pack 42", "unit_price_cents": 1250}
```

## Setup

```python
from problem_api import make_api
client = make_api().client()                             # 60 customers, 130 products, 250 orders
make_api(customers, products, orders).client()           # or your own small lists
```

The max page sizes are also exported as `MAX_ORDERS_LIMIT`,
`MAX_CUSTOMERS_PER_PAGE`, `MAX_PRODUCTS_LIMIT` (100 / 50 / 100). The
`if __name__ == "__main__":` block is what the Run button executes: fetch one
small page of each endpoint there and compare the three envelopes.

## Your task

Your module must define:

* `class ApiError(Exception)`: constructor `ApiError(status, path, message="")`;
  attributes `.status: int`, `.path: str` (the path without query string).
* `build_report(client: httpx.Client) -> dict`: returns
  `{"customers": [...], "orphans": [...]}`.

Rules:

* **customers**: one row for **every** customer from `/v1/customers`, sorted by
  `customer_id`:
  `{"customer_id", "name", "tier", "orders", "total_cents", "top_product"}`.
  * `orders`: number of the customer's (non-orphan) orders.
  * `total_cents`: sum of `qty * unit_price_cents` over all their order items.
  * `top_product`: the `product_id` with the highest **total qty** across
    their orders, ties broken by `product_id` ascending; `None` if no orders.
  * A customer with no orders: `orders 0`, `total_cents 0`, `top_product None`.
* **orphans**: orders that can't be joined, sorted by `order_id`:
  `{"order_id", "reason", "ref"}`.
  * Unknown `customer_id` → `reason "unknown_customer"`, `ref` = that customer id.
    This is checked first.
  * Otherwise, any item with an unknown `product_id` →
    `reason "unknown_product"`, `ref` = the **first** unknown product id in
    item order.
  * An orphaned order counts towards nothing in `customers`.
* Read each collection with its list endpoint at its **maximum page size**,
  each page exactly once. Never call the per-id endpoints.
* Any non-2xx response raises `ApiError(status, path)`.

## Example

Customers `cus_a` (Acme, pro) and `cus_c` (Cora, free); products `p1` at 250
and `p2` at 1000 cents; order `o1`: `cus_a` buys `p2` x1 + `p1` x3; order
`o2`: deleted `cus_x` buys `p1` x1.

```python
build_report(make_api(customers, products, orders).client())
# customers: [{"customer_id": "cus_a", "name": "Acme", "tier": "pro", "orders": 1, "total_cents": 1750, "top_product": "p1"},
#             {"customer_id": "cus_c", "name": "Cora", "tier": "free", "orders": 0, "total_cents": 0, "top_product": None}]
# orphans:   [{"order_id": "o2", "reason": "unknown_customer", "ref": "cus_x"}]
```

## Constraints

* Go through HTTP only; don't read `api.orders` / `api.customers` / `api.products`.
* The default `make_api()` has 60 customers, 130 products and 250 orders, so
  every collection needs more than one page at the maximum page size.

<details><summary>Hint 1</summary>

Write one small generator per endpoint (`iter_orders`, `iter_customers`,
`iter_products`), each knowing only its own pagination style. Then build
`{id: record}` dicts for customers and products and stream the orders past them.
</details>

<details><summary>Hint 2</summary>

Stop conditions: cursor → `next_cursor` is null; page → `page >= total_pages`;
offset → `offset >= total` (or an empty page). `collections.Counter` is handy
for both the order counts and the per-product quantities.
</details>

## Follow-up (talk it through)

* You load every customer and product into memory. When does that stop
  working, and what would you do instead?
* Orders are paginated live while customers might be created mid-crawl. In
  what order should you fetch the three collections, and why?
* Finance asks whether orphans should be dropped, retried later, or block
  the report. How would you decide?
