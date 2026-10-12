# 03. Search orders with query filters

The billing dashboard needs a "find orders" panel: filter by status, date
range, minimum total, and optionally show archived orders. The Orders API
supports all of that through **query parameters**. Your job is the thin
client function that turns Python arguments into exactly the right query
string, and nothing more.

Where does data go in a request?

* **Path**: *which* resource: `/v1/orders/ord_001`.
* **Query string**: *how* to read a collection (filters, sorting, paging):
  `/v1/orders?status=paid&sort=-total_cents`. Always strings.
* **JSON body**: the data you're creating or changing (`POST`/`PUT`/`PATCH`).
  A `GET` has no body.

## The API

`GET /v1/orders` returns `{"data": [order, ...], "count": n}` where an order is

```json
{"id": "ord_003", "customer": "acme-labs", "status": "shipped",
 "total_cents": 45000, "created_at": "2024-03-02T07:15:00Z", "archived": false}
```

| param | format | meaning |
|---|---|---|
| `status` | repeat it: `status=paid&status=shipped` | any of `pending`, `paid`, `shipped`, `refunded` |
| `since` / `until` | `2024-03-01T09:00:00Z` (UTC, `Z` suffix, whole seconds) | `since <= created_at < until` |
| `min_total_cents` | integer | `total_cents >= min_total_cents` |
| `include_archived` | `true` / `false` | default `false` |
| `sort` | `created_at`, `-created_at`, `total_cents`, `-total_cents` | default `created_at` |

The server answers **400** with an explanation for unknown parameters or bad
values (e.g. `status=paid,shipped`).

## Setup

```python
from problem_api import make_api
client = make_api().client()   # an httpx.Client wired to the mock Orders API
```

The `if __name__ == "__main__":` block is what the Run button executes: use
it to `client.get("/v1/orders", params=...)` and see the raw data and the
400s the server sends for bad parameters.

## Your task

Your module must define:

* `SORTS = ("created_at", "-created_at", "total_cents", "-total_cents")`
* `search_orders(client: httpx.Client, *, status: list[str] | None = None, since: datetime | None = None, until: datetime | None = None, min_total_cents: int | None = None, include_archived: bool | None = None, sort: str | None = None) -> list[dict]`
  (everything after `client` is keyword-only)

Rules:

* Send **only the arguments that were given** (`None` means "don't send it").
  Careful: `min_total_cents=0` and `include_archived=False` *were* given.
* `status`: one `status=` param per value, in the order given. An empty list sends nothing.
* `since` / `until`: must be **timezone-aware**; convert to UTC and format as
  `YYYY-MM-DDTHH:MM:SSZ` (drop microseconds). A naive datetime raises `ValueError`.
* `include_archived`: `"true"` / `"false"`, lower-case.
* `sort` not in `SORTS`, or a negative `min_total_cents`: raise `ValueError`.
* Every `ValueError` happens **before** any request is sent.
* Non-2xx: call `resp.raise_for_status()` (raises `httpx.HTTPStatusError`).
* Return the `data` list as the server sent it (the server filters and sorts).

## Example

```python
ist = timezone(timedelta(hours=5, minutes=30))
search_orders(client, status=["paid", "shipped"], since=datetime(2024, 3, 4, 0, 0, tzinfo=ist),
              include_archived=False, sort="-total_cents")
# GET /v1/orders?status=paid&status=shipped&since=2024-03-03T18:30:00Z&include_archived=false&sort=-total_cents
# -> [ord_008 (31000), ord_012 (22000), ord_009 (5000)]
```

## Constraints

* Let httpx build the query string (`params=`), don't concatenate strings into the URL.
* Don't filter or sort on the client: the server does it.

<details><summary>Hint 1</summary>

httpx accepts a list for a repeated key: `params={"status": ["paid", "shipped"]}`
sends `status=paid&status=shipped`. A list of `(key, value)` tuples works too.
</details>

<details><summary>Hint 2</summary>

`dt.tzinfo is None` (or `dt.utcoffset() is None`) means naive. Then
`dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`.
Watch `if min_total_cents:` vs `if min_total_cents is not None:`.
</details>

## Follow-up (talk it through)

* Some APIs take `status=paid,shipped`, others `status[]=paid`. How do you find
  out which one an API wants, and what happens if you guess wrong?
* Why does the server define `until` as exclusive? What breaks with an
  inclusive end when you page through days?
* Why reject naive datetimes instead of assuming UTC?
