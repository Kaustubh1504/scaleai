# 33. asyncio fan-out with a semaphore

An eval job needs the full text of a few hundred **model responses** before it
can score them. The Responses API only serves one response per call, and the
provider allows at most `limit` concurrent connections per key. Write the
async fetcher: fan out with `asyncio`, but never exceed the limit.

## The API

`GET /v1/responses/{response_id}` → `200`

```json
{"id": "resp_0003", "prompt_id": "prm_0002", "model": "model-b",
 "text": "Answer #3", "tokens": 79}
```

* Unknown id → **404** `{"error": "response resp_9999 not found"}`.
* Latency varies per id, so responses finish **out of order**.

## Setup

```python
from problem_api import make_api
api = make_api(n_responses=100)        # resp_0001 .. resp_0100 exist
async with api.async_client() as client: ...   # inside an async def run via asyncio.run
```

Tests check `api.max_in_flight` to see how many requests overlapped. The
`if __name__ == "__main__":` block is what the Run button executes: fetch one
response and a 404 there with `asyncio.run(main())`.

## Your task

Your module must define:

* `class ApiError(Exception)`: constructor `ApiError(status, response_id, message="")`;
  attributes `.status: int` (HTTP status) and `.response_id: str` (the id that failed).
* `async def fetch_all(client: httpx.AsyncClient, ids: list[str], limit: int = 5) -> list[dict]`
  (must be a coroutine function).

* Return the JSON body for each id, **in input order**.
* At most `limit` requests in flight at any moment; with enough ids you
  should actually reach `limit` (that's the point of the fan-out).
* Use `asyncio.gather` and an `asyncio.Semaphore(limit)` **created inside
  the function** (so it belongs to the running event loop).
* `[]` returns `[]` with no requests. `limit < 1` raises `ValueError`.
* Any non-2xx response raises `ApiError` with `.status` and `.response_id`.
* No deduping: one request per input id.

## Example

```python
await fetch_all(client, ["resp_0004", "resp_0001"], limit=2)
# [{"id": "resp_0004", ...}, {"id": "resp_0001", ...}]
```

## Constraints

* No threads; one event loop. Never call `time.sleep` in async code.
* Don't read `api.records`. Go through HTTP only.

<details><summary>Hint 1</summary>

Write a small inner coroutine that does one request inside `async with sem:`,
then `gather` one call of it per id. `gather` returns results in the order you passed the awaitables, not
completion order.
</details>

<details><summary>Hint 2</summary>

`gather` vs `TaskGroup` (3.11+): with plain `gather`, the first exception is
raised to you but the **other tasks keep running**. A `TaskGroup` cancels the
siblings and raises an `ExceptionGroup`. `gather(..., return_exceptions=True)`
never raises: it puts exception objects in the result list for you to sort
through (that's problem 34's territory).
</details>

## Follow-up (talk it through)

* `asyncio.gather(*[...])` over 100k ids creates 100k tasks up front. What's
  the memory cost, and how would a bounded worker pool + `asyncio.Queue` fix it?
* How would you add a per-request timeout (`asyncio.wait_for` /
  `asyncio.timeout`) and what should a timeout cancel?
* Why is a semaphore around the request better than batching into chunks of
  `limit` and gathering each chunk?
