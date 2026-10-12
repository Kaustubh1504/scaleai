# 21. Group and aggregate orders

Finance wants three numbers out of the labeling-service order log before the
quarterly business review: revenue per customer per month, the top customers
in each region, and a per-month summary. You don't have pandas, the
timestamps come from offices in different timezones, and the numbers have to
match the finance team's spreadsheet **to the cent**, every time you run it.

## Input

A list of order dicts (see `problem_api.ORDERS`), in no particular order:

```python
{"order_id": "ord_04", "customer_id": "cus_bolt", "region": "us-east",
 "created_at": "2024-01-31T22:30:00-05:00", "total_cents": 15000}
```

* `created_at` is ISO 8601 and always has a zone: `Z` or `±HH:MM`.
* `total_cents` is a non-negative int.

## Setup

```python
from problem_api import ORDERS      # 11 orders, unsorted
```

No HTTP: pure functions over a list. The `if __name__ == "__main__":` block is
what the Run button executes: print the orders there and spot which
timestamps land in a different month once converted to UTC.

## Your task

Your module must define:

* `revenue_by_customer_month(orders: list[dict]) -> dict[str, dict[str, int]]`
* `top_customers_per_region(orders: list[dict], k: int = 3) -> dict[str, list[tuple[str, int]]]`
* `monthly_summary(orders: list[dict]) -> list[dict]`

Rules:

* **Months are UTC months**, formatted `"YYYY-MM"`. `ord_04` above is
  `2024-02-01T03:30Z`, so it belongs to `"2024-02"`.
* **`revenue_by_customer_month`**: `{customer_id: {month: summed cents}}`.
  Outer keys sorted by customer id, inner keys sorted by month (dict
  insertion order is what's checked). Only months with orders appear.
* **`top_customers_per_region`**: for each region, sum each customer's
  cents **within that region** (a customer can appear in several regions).
  Return the top `k` as `(customer_id, cents)` tuples, highest cents first,
  **ties broken by customer id ascending**. Fewer than `k` customers → all of
  them. Region keys sorted. `k < 1` raises `ValueError`.
* **`monthly_summary`**: one dict per month, sorted by month:
  `{"month", "count", "total_cents", "average_cents", "median_cents"}`.
  * `average_cents` = total / count, **rounded half-up** to a whole cent
    (`10000.5 → 10001`). Note Python's `round()` rounds half to *even*.
  * `median_cents` = the middle value; for an even count, the mean of the two
    middle values, rounded half-up the same way.
  * All values are ints.
* Empty input gives `{}`, `{}` and `[]`. Don't mutate the input.

## Example

```python
revenue_by_customer_month(ORDERS)["cus_echo"]   # {"2023-12": 4500, "2024-03": 7000}
top_customers_per_region(ORDERS)["us-east"]     # [("cus_bolt", 15002), ("cus_dune", 15002), ("cus_acme", 15000)]
monthly_summary(ORDERS)[2]
# {"month": "2024-02", "count": 4, "total_cents": 40002, "average_cents": 10001, "median_cents": 10000}
```

## Constraints

* Standard library only (`collections`, `datetime`, `statistics`, `decimal` are fine).
* Must work on Python 3.10, where `datetime.fromisoformat` doesn't accept `"Z"`.

<details><summary>Hint 1</summary>

A nested `defaultdict` gives you the sums in one line per order. Build the
output by iterating over sorted items, so ordering is explicit rather than an
accident of input order.
</details>

<details><summary>Hint 2</summary>

Sort by a tuple key, (negative cents, id), for "cents descending, then id
ascending". For half-up rounding of `a / b` with non-negative ints,
`(2 * a + b) // (2 * b)` is exact (`Decimal` with `ROUND_HALF_UP` works too).
</details>

## Follow-up (talk it through)

* Finance's spreadsheet groups by *local* month for each region. How would
  that change the code, and which is "right"?
* Why integer cents rather than float dollars? Where do floats bite here?
* The log is 50 GB. Which of these three functions can you compute in one
  streaming pass with bounded memory, and which can't you (hint: median)?
