# 09. Cursor pagination with a loop guard

You're pulling every event out of a third-party **Events API** so you can load
it into the warehouse. The API uses **cursor pagination**. The provider also
has a known bug: under load it sometimes returns the *same* cursor you just
sent, and a naive client loops forever.

## The API

`GET /v1/events?limit=<1..100>&cursor=<opaque string>`

* Header `X-API-Key: <key>` is required. Without it you get **401**.
* Omit `cursor` on the first request.
* A `limit` outside `1..100` is **400**.

```json
{
  "results": [{"id": "evt_0001", "type": "created", "seq": 1}, ...],
  "next_cursor": "bzoyMA"
}
```

`next_cursor` is `null` on the last page. Treat cursors as opaque: never
parse or build them yourself.

## Setup

```python
from problem_api import make_api, API_KEY
client = make_api(n_events=123).client()   # API_KEY == "key_live_123"
```

`make_api(..., loop_at_page=3)` reproduces the repeated-cursor bug. The
`if __name__ == "__main__":` block is what the Run button executes: print a
raw page (e.g. `limit=3`) first.

## Your task

Your module must define:

* `class ApiError(Exception)`: `ApiError(status, path, message="")`; attributes
  `.status: int` (HTTP status) and `.path: str` (request path, e.g. `"/v1/events"`).
* `class PaginationLoopError(Exception)`: no extra attributes.
* `iter_events(client: httpx.Client, api_key: str, limit: int = 50) -> Iterator[dict]`
* `fetch_all_events(client: httpx.Client, api_key: str, limit: int = 50) -> list[dict]`

Rules:

* Send `X-API-Key: <api_key>` on every request.
* `iter_events` is a **generator**. It yields events one at a time, in API
  order, and requests the next page only when the caller needs it.
* Send every request through `client` (its `base_url` is already set). Pass
  `limit` on every request.
* Any non-2xx response raises `ApiError` with `.status` and `.path` set.
* If the server returns a `next_cursor` you have **already sent**, raise
  `PaginationLoopError` instead of requesting it again.
* `fetch_all_events` returns `list(iter_events(...))`.

## Example

```python
fetch_all_events(make_api(n_events=5).client(), API_KEY, limit=2)
# 3 requests: cursor=None -> 2 events, cursor=A -> 2 events, cursor=B -> 1 event (next_cursor null)
# -> [{"id": "evt_0001", ...}, ..., {"id": "evt_0005", ...}]
```

## Constraints

* Don't read `api.events` or other mock internals. Go through HTTP only.
* An empty last page (`"results": []` with `next_cursor: null`) is normal.

<details><summary>Hint 1</summary>

Loop: request a page, yield its results, stop when `next_cursor` is `None`.
Keep a `set` of the cursors you've sent and check the new one against it.
</details>

<details><summary>Hint 2</summary>

Watch out: httpx sends `{"cursor": None}` as `?cursor=` (an empty value), so add `cursor` to
`params` only when you have one.
</details>

## Follow-up (talk it through)

* What can go wrong if records are inserted while you paginate with **offset**
  pagination? Why are cursors safer?
* The crawl dies on page 400 of 900. How would you resume without starting over?
