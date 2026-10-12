# 07. Page-number pagination

The pricing team wants a nightly snapshot of every product in the **Catalog
API** (labeling packs customers can buy). The API uses classic **page-number
pagination**. It is mostly well behaved, but the backend counts pages from a
cache, so `total_pages` is occasionally a little off.

## The API

`GET /v1/products?page=<1..>&per_page=<1..100>`

* Header `X-API-Key: <key>` is required. Without it you get **401**.
* Pages are **1-based**. `per_page` outside `1..100` is **400**.

```json
{
  "data": [{"id": "prd_0001", "name": "Labeling pack 1", "category": "text", "price_cents": 525}, ...],
  "page": 1,
  "per_page": 20,
  "total": 47,
  "total_pages": 3
}
```

* For an empty catalog, `total_pages` is **0** (and `data` is `[]`).
* Sometimes `total_pages` is one too high and the last page comes back with
  `"data": []`.
* Rarely, a page **before** `total_pages` comes back with `"data": []`.

## Setup

```python
from problem_api import make_api, API_KEY
client = make_api(n_products=47).client()   # API_KEY == "key_live_123"
```

`make_api` also takes `extra_empty_page=True` / `empty_from_page=n` to
reproduce the quirks below. The `if __name__ == "__main__":` block is what the
Run button executes: print a raw page (and an empty catalog's page 1) first.

## Your task

Your module must define:

* `class ApiError(Exception)`: `ApiError(status, path, message="")`; attributes
  `.status: int` (HTTP status) and `.path: str` (request path, e.g. `"/v1/products"`).
* `fetch_all_products(client: httpx.Client, api_key: str, per_page: int = 20) -> list[dict]`

Rules:

* Request page 1, 2, 3, ... in order, passing `page` and `per_page` on every
  request. Never request the same page twice.
* Return every product, in API order.
* Stop after page `total_pages` (read it from the response you just got).
  An empty catalog (`total_pages: 0`) costs exactly **one** request.
* Also stop as soon as a page returns empty `data`, even if `total_pages`
  says there is more. Don't request the next page.
* Any non-2xx response raises `ApiError` with `.status` and `.path` set.

## Example

```python
fetch_all_products(client, API_KEY, per_page=20)   # 47 products
# 3 requests: page=1 (20), page=2 (20), page=3 (7) -> total_pages is 3, stop
# -> [{"id": "prd_0001", ...}, ..., {"id": "prd_0047", ...}]
```

## Constraints

* Go through HTTP only. Don't read `api.products` or other mock internals.
* No retries in this problem: an error simply raises.

<details><summary>Hint 1</summary>

Loop forever from page 1: fetch, keep the data, then stop if the page was
empty or this page is the last one `total_pages` admits; otherwise move on.
Check the empty case **before** you trust `total_pages`.
</details>

<details><summary>Hint 2</summary>

`while page <= total_pages` with `total_pages` initialised to 1 is the
classic off-by-one trap: think through what happens when the server says 0.
</details>

## Follow-up (talk it through)

* A product is inserted at position 5 while you are on page 3. What do you
  get? What about a deletion? How would you detect or tolerate it?
* Pages are independent here. How would you fetch them concurrently, and why
  do you still need page 1 first?
* When would you choose `per_page=100` over 20, and what's the cost?
