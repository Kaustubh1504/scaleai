# Calling Flaky APIs in Python: Retries, Pagination, and Concurrency, Step by Step

### Four small functions that make any third-party API safe to depend on

Every backend eventually depends on someone else's API, and every API eventually has a bad day: rate limits, 502s, slow responses, pagination that loops forever. In this tutorial we'll build four standalone functions, one step at a time:

1. `request_with_retries()`: any HTTP call, retried safely
2. `fetch_all_pages()`: follow cursor pagination without infinite loops
3. `bounded_map()`: run many calls in parallel, but only N at a time
4. `bounded_gather()`: the same thing for async code

**What you need:** Python 3.9+ and `pip install httpx`.

---

## Part 1: Retries

### Step 1: The naive call

```python
r = httpx.get(f"{base}/customers/{cid}")
customer = r.json()
```

If the API returns a 503, `r.json()` might be an HTML error page, and your code crashes. If the network drops, `httpx` raises an exception. Neither should take down your request.

### Step 2: Decide what's worth retrying

Before writing a loop, sort the possible failures into two groups:

- **Temporary, so retry:** 429 Too Many Requests, any 5xx, timeouts, connection errors.
- **Permanent, so don't retry:** 400, 401, 403, 404, 422. The same request will fail the same way every time.

### Step 3: Write the loop

```python
for attempt in range(retries + 1):
    try:
        r = http.request(method, url, **kwargs)
    except httpx.TransportError:          # timeouts + connection errors
        continue
    if r.status_code != 429 and r.status_code < 500:
        return r                          # success OR permanent failure: stop
return None                               # every attempt failed
```

Notice that the loop doesn't decide what *success* means. It returns the first response that isn't worth retrying, and lets the caller judge it. A 404 might be an error for one caller and an answer ("customer doesn't exist") for another.

### Step 4: Wait longer between attempts

Retrying instantly makes an overloaded server worse. Wait with exponential backoff: 0.5 s, 1 s, 2 s…

```python
    if attempt:
        time.sleep(backoff * 2 ** (attempt - 1))
```

> **Production tip:** add jitter (`random.uniform(d / 2, d)`) so a thousand clients that failed together don't all retry at the same instant. If a 429 response includes a `Retry-After` header, wait that long instead.

### Step 5: Default timeout, and close what you open

Always set a timeout; otherwise a slow server can hang the call far longer than you'd expect. Accept an optional client so tests can inject a fake one, and close the client only if you created it.

### The complete function

```python
import time

import httpx


def request_with_retries(method: str, url: str, *, retries: int = 3, backoff: float = 0.5,
                         client=None, **kwargs):
    """Retry 429 / 5xx / timeouts / connection errors with exponential backoff.

    Returns the first non-retryable Response (2xx or another 4xx) for you to judge,
    or None if every attempt failed. kwargs go to httpx: json=, params=, headers=, content=, timeout=
    """
    http = client or httpx.Client()
    kwargs.setdefault("timeout", 10)
    try:
        for attempt in range(retries + 1):
            if attempt:
                time.sleep(backoff * 2 ** (attempt - 1))
            try:
                r = http.request(method, url, **kwargs)
            except httpx.TransportError:
                continue
            if r.status_code != 429 and r.status_code < 500:
                return r
        return None
    finally:
        if client is None:
            http.close()
```

### Step 6: Turn the result into a decision

Because the function returns the response rather than a bare `True`/`False`, each caller can map outcomes to whatever its own error handling needs:

```python
r = request_with_retries("GET", f"{base}/customers/{cid}", headers={"Authorization": f"Bearer {token}"})
if r is None:
    customer, err = None, "upstream_unavailable"     # network / 429 / 5xx even after retries
elif r.status_code == 404:
    customer, err = None, "unknown_customer"
elif r.is_success:
    customer, err = r.json(), None
else:
    customer, err = None, "upstream_error"
```

---

## Part 2: Pagination

### Step 7: Follow the cursor

Most list APIs return a page of items plus a cursor for the next page. The basic loop:

```python
items, cursor = [], None
while True:
    body = httpx.get(url, params={"cursor": cursor} if cursor else {}).json()
    items.extend(body["data"])
    cursor = body.get("next_cursor")
    if not cursor:
        break
```

### Step 8: Guard against loops

If the API has a bug and returns the same cursor twice, this runs forever and burns through your rate limit. Track the cursors you've already seen, and cap the total page count:

```python
def fetch_all_pages(fetch_page, max_pages: int = 10_000) -> list:
    """fetch_page(cursor) -> (items, next_cursor). Stops on a falsy cursor; guards against loops."""
    items, cursor, seen = [], None, set()
    for _ in range(max_pages):
        page_items, cursor = fetch_page(cursor)
        items.extend(page_items)
        if not cursor:
            return items
        if cursor in seen:
            raise RuntimeError(f"repeated cursor {cursor!r}")
        seen.add(cursor)
    raise RuntimeError("too many pages")
```

The function doesn't know about HTTP. You pass in a small `fetch_page(cursor)` function, so it works with any API shape:

```python
def page(cursor):
    r = request_with_retries("GET", url, params={"cursor": cursor} if cursor else {})
    if r is None or not r.is_success:
        raise RuntimeError("page fetch failed")
    body = r.json()
    return body["data"], body.get("next_cursor")

everything = fetch_all_pages(page)
```

---

## Part 3: Doing many calls at once

### Step 9: Sequential is too slow

200 items × 1 second per call = more than 3 minutes:

```python
results = [enrich(item) for item in items]
```

### Step 10: Unbounded is dangerous

Starting all 200 calls at once gets you rate-limited, or knocks over a small server. You want **N at a time**.

### Step 11: A bounded thread pool, with results in order

```python
from concurrent.futures import ThreadPoolExecutor


def bounded_map(fn, items, max_workers: int = 5) -> list:
    """fn(item) for every item, at most max_workers at once, results in input order."""
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(fn, items))
```

`max_workers` caps how many calls are in flight. `pool.map` returns results **in input order**, no matter which call finishes first. That matters when the output has to line up with the input.

```python
results = bounded_map(enrich, items, max_workers=5)
```

### Step 12: The async version

If your code is `async`, an `asyncio.Semaphore` does the same job:

```python
import asyncio


async def bounded_gather(fn, items, limit: int = 5) -> list:
    """await fn(item) for every item, at most `limit` at once, results in input order."""
    sem = asyncio.Semaphore(limit)

    async def run(item):
        async with sem:
            return await fn(item)

    return await asyncio.gather(*(run(i) for i in items))
```

`asyncio.gather` also preserves order. To use a sync function (like `request_with_retries`) from async code, wrap it in `asyncio.to_thread`:

```python
results = await bounded_gather(lambda item: asyncio.to_thread(enrich, item), items, limit=5)
```

---

## Step 13: Test the limits, not just the results

Use the `fake_http` helper from the first article in this series. It records every request and the highest number in flight at once. Add a small delay so calls actually overlap:

```python
def test_retries():
    client, stats = fake_http([502])
    assert request_with_retries("GET", "http://x", backoff=0, client=client) is None
    assert len(stats["requests"]) == 4                    # 1 + 3 retries

    client, stats = fake_http([500, 404])
    assert request_with_retries("GET", "http://x", backoff=0, client=client).status_code == 404
    assert len(stats["requests"]) == 2                    # 404 is not retried


def test_concurrency_is_bounded_and_ordered():
    client, stats = fake_http([200], delay=0.02)
    out = bounded_map(lambda i: (i, client.get("http://x").status_code), range(30), 5)
    assert out == [(i, 200) for i in range(30)]           # input order kept
    assert 1 < stats["max_in_flight"] <= 5                # parallel, but bounded
```

The `> 1` check matters too: it proves the calls really ran in parallel and didn't silently fall back to sequential.

---

## Recap

1. **Retry only** 429s, 5xx errors and network errors, with exponential backoff.
2. **Return the response** and let each caller decide what it means.
3. **Guard pagination** against repeated cursors.
4. **Bound concurrency** and keep input order, using threads for sync code and a semaphore for async.
5. **Test the call counts and the in-flight maximum,** not just the final result.

*Next: signed webhooks with idempotency keys.*
