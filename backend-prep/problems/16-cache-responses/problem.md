# 16. Cache responses: dedupe lookups and a TTL cache

The finance dashboard shows the last 500 orders with the customer's name and
tier next to each. The first version called `GET /v1/users/{id}` once **per
order**: 500 requests for about 40 customers, and the Users team noticed.
Fetch each user once. Then build a small TTL cache the service can keep
between requests.

## The API

`GET /v1/users/{user_id}`: `{"id": "usr_001", "name": "Customer 1", "email": "c1@example.com", "tier": "pro"}`.
A few orders point at **deleted** users, which return **404**.

Orders (from `make_orders()`):

```json
[{"id": "ord_0001", "user_id": "usr_024", "total_cents": 30850}, ...]
```

## Setup

```python
from problem_api import make_api, make_orders
api = make_api(); client = api.client(); orders = make_orders()   # 500 orders
```

`problem_api.DANGLING_USER_IDS` lists the deleted user ids the orders point
at. `TTLCache` takes a clock: call only `clock.time()` (tests pass a
`kit.FakeClock` and move it with `clock.advance(s)`). The
`if __name__ == "__main__":` block is what the Run button executes: count the
distinct `user_id`s and look at a 404 there.

## Your task

Your module must define:

* `class ApiError(Exception)`: constructor `ApiError(status, path, message="")`;
  attributes `.status: int`, `.path: str`.
* `enrich_orders(client: httpx.Client, orders: list[dict]) -> list[dict]`
* `class TTLCache`: `TTLCache(clock, ttl_s: float, max_items: int | None = None)`
  * `.get(key, default=None)`
  * `.set(key, value) -> None`
  * `.get_or_load(key, loader: Callable[[], Any])`

**`enrich_orders`**

* Returns a **new** list, same order, where each item is the order's fields
  plus `"user"`: the user dict, or `None` if the user is a 404. Don't mutate
  the input.
* Request each distinct `user_id` **at most once**, including the 404s.
  Remembering "not found" is **negative caching**.
* Any other non-2xx raises `ApiError(status, path)`.

**`TTLCache`**

* `set(key, value)` stores the value with `expires_at = clock.time() + ttl_s`
  (re-setting a key replaces it and restarts its TTL).
* `get(key, default=None)` returns the value while `clock.time() < expires_at`.
  At or after `expires_at` the entry is gone: return `default`.
* `get_or_load(key, loader)` returns a fresh cached value, or calls `loader()`
  once, stores its result and returns it. A result of `None` is cached too.
* `max_items`: if a `set` makes the cache hold more than `max_items` keys,
  evict the **least recently used** one. A `set` or a `get` that hits counts as
  a use. `None` means unbounded.

## Example

```python
enrich_orders(client, make_orders())[0]
# {"id": "ord_0001", "user_id": "usr_024", "total_cents": 30850, "user": {"id": "usr_024", ...}}
len(api.log)            # 42: one per distinct user_id, not 500

cache = TTLCache(clock, ttl_s=60)
cache.set("a", 1)       # at t
clock.advance(59.9); cache.get("a")   # 1
clock.advance(0.1);  cache.get("a")   # None: expired exactly at t + 60
```

## Constraints

* Go through HTTP only. Don't read `api.users`.
* Use `clock.time()`, never the `time` module.

<details><summary>Hint 1</summary>

Test membership (`user_id in cache`), not truthiness: a cached `None` is
falsy, so a truthiness check re-fetches every 404. `get_or_load` has the same
trap; a private sentinel object lets you tell "missing" from "cached `None`".
</details>

<details><summary>Hint 2</summary>

`collections.OrderedDict` has `move_to_end(key)` and `popitem(last=False)`,
which is all of LRU.
</details>

## Follow-up (talk it through)

* How long should a negative cache entry live compared with a positive one? Why?
* The cache lives in one process, but the service runs on 8 pods. What changes?
* Instead of caching, could you avoid N lookups altogether? (Batch endpoints,
  `?ids=a,b,c`, ...)
