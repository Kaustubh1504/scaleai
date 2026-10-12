# 08. Offset/limit pagination with a lying total

The quality team audits every annotation on the platform. The **Annotations
API** uses offset/limit pagination, and it has two quirks that have bitten
people before:

1. It **silently caps** `limit` at 50. Ask for 100 and you get 50 items back
   (and `"limit": 50` in the envelope). No error.
2. `total` comes from a slow-to-update counter. It can be **lower or higher**
   than the real number of annotations. Don't trust it.

## The API

`GET /v1/annotations?offset=<0..>&limit=<1..>`

* Header `X-API-Key: <key>` is required. Without it you get **401**.
* `offset < 0` or `limit < 1` is **400**.

```json
{
  "items": [{"id": "ann_00001", "task_id": "task_0001", "label": "dog", "annotator": "user_2"}, ...],
  "offset": 0,
  "limit": 50,
  "total": 130
}
```

`limit` in the response is the limit the server **actually applied**.

## Setup

```python
from problem_api import make_api, API_KEY
client = make_api(n_annotations=130).client()   # API_KEY == "key_live_123"
```

`make_api(..., reported_total=90)` makes the server lie about `total`. The
`if __name__ == "__main__":` block is what the Run button executes: print a
raw page (try `limit=100`) before writing the loop.

## Your task

Your module must define:

* `class ApiError(Exception)`: `ApiError(status, path, message="")`; attributes
  `.status: int` (HTTP status) and `.path: str` (request path, e.g. `"/v1/annotations"`).
* `fetch_all_annotations(client: httpx.Client, api_key: str, limit: int = 50) -> list[dict]`

Rules:

* Send `X-API-Key: <api_key>` on every request.
* Start at `offset=0`. Send `offset` and your `limit` on every request.
* After each page, advance `offset` by the **number of items actually
  returned** (not by the limit you asked for).
* Stop when a page is empty, or has fewer items than the `limit` **the
  server reported** in that response.
* Ignore `total` for deciding when to stop.
* Return every annotation, in API order. Any non-2xx raises `ApiError`.

## Example

```python
fetch_all_annotations(client, API_KEY, limit=100)   # 130 annotations
# offset=0   -> 50 items, limit 50 (capped!)
# offset=50  -> 50 items
# offset=100 -> 30 items  < 50: stop.   3 requests, 130 annotations
```

## Constraints

* Go through HTTP only. Don't read `api.annotations` or other mock internals.
* No retries in this problem: an error simply raises.

<details><summary>Hint 1</summary>

If you advance by the `limit` you asked for (100), you skip items 50–99 and
never notice. Advance by `len(items)`.
</details>

<details><summary>Hint 2</summary>

If the total divides evenly (100 items, pages of 50), the last real page is
full, so you need one more request that comes back empty. That's expected.
</details>

## Follow-up (talk it through)

* Why does offset pagination get slow on deep pages, and what happens to your
  crawl if rows are inserted or deleted mid-way?
* `total` is wrong. When is it still useful (progress bars, sanity checks)?
* How would you verify, after the crawl, that you didn't miss or duplicate anything?
