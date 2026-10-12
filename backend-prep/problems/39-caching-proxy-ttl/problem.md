# 39. Caching proxy with TTL and stale fallback

The pricing page calls an internal **Catalog API** that is slow and falls over
under load. Put a small caching proxy in front of it: serve repeat reads from
memory, and when the upstream is down, keep serving the last good copy rather
than an error.

## The API (upstream)

`GET /v1/products/{product_id}` on the `httpx.Client` you're given (its
`base_url` is set):

```json
200 {"id": "p1", "name": "Bounding-box QA pack", "price_cents": 1200, "stock": 14}
404 {"error": "no product p9"}
```

It can also answer 5xx/429, time out, refuse connections, or return a
truncated (non-JSON) 200 body.

## Setup

```python
from kit import FakeClock; from problem_api import make_api
api, clock = make_api(), FakeClock()       # api.script("GET /v1/products/p1", [503]) injects failures
c = TestClient(create_app(api.client(), clock, ttl_s=30))   # how the tests build your app
```

`api.client()` is an `httpx.Client` with `base_url` set; `api.calls("GET", path)`
lists upstream calls; `clock.advance(s)` moves time. Your file starts empty. An
`if __name__ == "__main__":` block is what the Run button executes: use it to hit
the raw upstream, then your proxy.

## Your task

Write in your file:

* `create_app(upstream: httpx.Client, clock, ttl_s: float = 30, negative_ttl_s: float = 5) -> FastAPI`
* `GET /products/{product_id}` → `200` / `404` / `502`, always with an `X-Cache` header.
* `POST /cache/purge/{product_id}` → `204`.

`GET /products/{product_id}` returns the product with a header
**`X-Cache: MISS | HIT | STALE`**. The cache holds at most one entry per id:
the latest upstream 200 (a *product*) or 404 (a *not-found*), plus
`stored_at = clock.time()` taken when that response arrived.

1. **Fresh entry** (`clock.time() < stored_at + ttl`, where ttl is `ttl_s` for
   a product and `negative_ttl_s` for a not-found): answer from the cache with
   `X-Cache: HIT` and **no upstream call**: `200` + the product, or `404`
   `{"detail": "product not found"}`.
2. Otherwise (no entry, or expired) call the upstream once:
   * `200` with a JSON body → store it, respond `200` + that body, `MISS`.
   * `404` → store a not-found, respond `404` `{"detail": "product not found"}`, `MISS`.
   * **anything else** is an upstream failure: any other status,
     `httpx.TransportError` (timeouts, connection errors), or a 200 whose body
     isn't valid JSON. The cache is left unchanged, and:
     * if the entry is a (expired) product → `200` + that old body, `X-Cache: STALE`;
     * otherwise → `502` `{"detail": "upstream unavailable"}`, `X-Cache: MISS`.
3. Serving stale does not refresh `stored_at`: the next request tries the upstream again.

`POST /cache/purge/{product_id}` → `204`, removing that id's entry (if any; an unknown id is still `204`).

## Example

```
GET /products/p1                        → 200 MISS   (upstream call 1)
+10 s:  GET /products/p1                → 200 HIT    (no call)
+20 s (now = stored_at + 30, expired), upstream scripted to 503:
        GET /products/p1                → 200 STALE, same body
GET /products/p9                        → 404 MISS; again within 5 s → 404 HIT
```

## Constraints

* Time comes only from `clock.time()`. Never `time.time()`.
* All state lives inside `create_app`. Talk to the upstream only through `upstream`.

<details><summary>Hint 1</summary>

A dict `product_id -> (status, body, stored_at)` is enough. Return
`JSONResponse(body, status_code=..., headers={"X-Cache": ...})` so you
control the header on every path.
</details>

<details><summary>Hint 2</summary>

Fold every failure into one place: wrap the upstream call and `resp.json()` in a
single `try` catching `(httpx.TransportError, ValueError)` (a non-JSON body raises
`ValueError`), return early on 200 and 404, and let everything else fall through
to one "serve stale or 502" path.
</details>

## Follow-up (talk it through)

* 500 requests for the same cold id arrive at once: they all miss and hammer
  the upstream (a *cache stampede*). How do you collapse them into one call?
* Should stale copies have a maximum age? What does `Cache-Control:
  stale-if-error` / `stale-while-revalidate` say about this design?
* Three replicas each have their own in-memory cache. What goes wrong, and when is Redis worth it?
