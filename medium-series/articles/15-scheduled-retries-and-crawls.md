# Scheduled Retries, Rate-Limited Crawls, and Async Fetching in Python, Step by Step

### Deliver webhooks without sleeping, crawl APIs that throttle you, and gather results without losing failures

Part 2 of this series retried *inside* a call, with `time.sleep` between attempts. That works for one request. It doesn't work for:

- a **webhook dispatcher** that must not block on a subscriber that's down for an hour,
- a **nightly crawl** against an API that rate-limits you, returns truncated bodies, and has a bad week,
- **async code**, where one `time.sleep` freezes every coroutine at once.

We'll build three standalone snippets: `retry_schedule`, `get_json_with_retries`, and `async_retries`.

**What you need:** Python 3.9+, `pip install httpx`.

---

## Part 1: Scheduled retries (no sleeping)

### Step 1: Store when to try again, not how long to wait

A dispatcher that sleeps 5 minutes for one dead subscriber delays everyone else. Instead, give each delivery a `next_attempt_at` timestamp. Each pass of `dispatch_due()` attempts only the deliveries that are due, and never sleeps.

```python
delivery = {"status": "pending", "attempts": 0, "next_attempt_at": None, "last_error": None}
```

### Step 2: Classify each attempt

- **2xx:** delivered.
- **408, 429, 5xx, connection errors, timeouts:** temporary, so retry later.
- **Anything else** (400, 404, 3xx, a malformed request): permanent, so mark it **dead** right away.

Specs differ on edge cases (is a timeout retryable?), so the snippet takes the lists as parameters.

### Step 3: Backoff with jitter and a cap

After attempt *n*, wait `min(cap, base * 2^(n-1))`, multiplied by a random factor in [0.5, 1.0]. With base 10 s that's 5–10 s, then 10–20 s, then 20–40 s, and so on up to the cap. The jitter keeps a thousand deliveries that failed together from all retrying in the same second.

### Step 4: `Retry-After` wins

If a 429 says `Retry-After: 30`, schedule exactly 30 seconds later. The header can also be an HTTP date. Then compute the wait relative to the response's own `Date` header, not your clock, because the two machines' clocks may disagree.

### Step 5: Count every attempt, then dead-letter

After `max_attempts` attempts (429s included), the delivery is `dead`, with `next_attempt_at = None` and `last_error` describing the final attempt.

### The complete snippet

```python
import random
import time
from email.utils import parsedate_to_datetime

import httpx


def classify_attempt(response=None, error=None,
                     retry_statuses=(408, 429), retry_errors=(httpx.ConnectError, httpx.TimeoutException)) -> str:
    """'ok' (2xx) | 'retry' (408, 429, 5xx, connection/timeout errors) | 'dead' (anything else)."""
    if error is not None:
        return "retry" if isinstance(error, retry_errors) else "dead"
    if 200 <= response.status_code < 300:
        return "ok"
    if response.status_code in retry_statuses or response.status_code >= 500:
        return "retry"
    return "dead"


def parse_retry_after(response):
    """Seconds from Retry-After: an integer, or an HTTP date minus the response's Date header. None if unusable."""
    value = response.headers.get("Retry-After", "").strip()
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value).timestamp()
    except (TypeError, ValueError, IndexError):
        return None
    try:
        base = parsedate_to_datetime(response.headers["Date"]).timestamp()
    except (KeyError, TypeError, ValueError, IndexError):
        base = time.time()
    return max(0.0, when - base)


def next_attempt_at(now: float, attempt: int, base: float = 10.0, cap: float = 300.0,
                    retry_after=None, rng=random.random) -> float:
    """After failed attempt number `attempt` (1-based): Retry-After wins exactly; otherwise
    now + min(cap, base * 2**(attempt-1)) * jitter, jitter uniform in [0.5, 1.0]."""
    if retry_after is not None:
        return now + retry_after
    return now + min(cap, base * 2 ** (attempt - 1)) * (0.5 + 0.5 * rng())


def record_attempt(delivery: dict, now: float, response=None, error=None, max_attempts: int = 5, **backoff) -> str:
    """Update {status, attempts, next_attempt_at, last_error} after one attempt; returns the new status."""
    delivery["attempts"] = delivery.get("attempts", 0) + 1
    outcome = classify_attempt(response, error)
    if outcome == "ok":
        delivery.update(status="delivered", next_attempt_at=None, last_error=None)
    else:
        delivery["last_error"] = f"HTTP {response.status_code}" if error is None else type(error).__name__
        if outcome == "dead" or delivery["attempts"] >= max_attempts:
            delivery.update(status="dead", next_attempt_at=None)
        else:
            ra = parse_retry_after(response) if response is not None and response.status_code == 429 else None
            delivery.update(status="pending",
                            next_attempt_at=next_attempt_at(now, delivery["attempts"], retry_after=ra, **backoff))
    return delivery["status"]


def due(deliveries, now: float) -> list:
    return [d for d in deliveries if d["status"] == "pending" and (d.get("next_attempt_at") or 0) <= now]
```

### Step 6: The dispatch loop

```python
def dispatch_due(deliveries, http, clock):
    now = clock.time()                                   # read once per pass
    for d in due(deliveries, now):                       # each due delivery at most once per pass
        body = json.dumps(d["event"], separators=(",", ":")).encode()
        try:
            r = http.post(d["url"], content=body, headers=signed_headers(d, body), timeout=5)
            record_attempt(d, now, response=r)
        except httpx.HTTPError as e:
            record_attempt(d, now, error=e)
        save_state_atomically(deliveries)                # before the next attempt
        append_audit_line(d)
```

Catch only `httpx.HTTPError`. A bug in your own code (a `KeyError`, say) should crash loudly rather than be recorded as a delivery failure.

---

## Part 2: Crawling a flaky, rate-limited API

### Step 7: Two separate budgets

During a crawl, *transient* failures (502s, timeouts, a truncated JSON body) and *rate limiting* (429s) need different handling:

- **Transient failures** share an attempt budget (for example 4), with jittered backoff.
- **429s** mean "you're fine, just slow down". Wait exactly what `Retry-After` says, and *don't* count it against the attempt budget. Do cap how many 429s you accept *in a row* (say 10), so a broken server can't keep you waiting forever.

### Step 8: A 200 with a broken body is a failure

`r.json()` raising on a truncated body is a transient failure, so retry it. Don't let it crash the crawl.

### Step 9: Everything else raises with the status attached

A 404, or a 401 that needs a token refresh, raises `ApiError` with `.status`, so the caller can decide what to do.

### Step 10: Inject `sleep` and `rng`

Tests pass `sleep=sleeps.append` and `rng=lambda: 1.0`. Then you can assert the exact wait sequence (0.5, 1, 2 seconds) without waiting.

### The complete snippet

```python
import random
import time
from email.utils import parsedate_to_datetime

import httpx


class ApiError(Exception):
    def __init__(self, status, url: str, detail: str = ""):
        super().__init__(f"{status} {url} {detail}".strip())
        self.status, self.url = status, url


def get_json_with_retries(http: httpx.Client, method: str, url: str, *, attempts: int = 4, max_429: int = 10,
                          transient=(500, 502, 503, 504), sleep=time.sleep, rng=random.random, **kwargs):
    """Parsed JSON of a 2xx response.
    Transient failures (transient statuses, transport errors, 2xx with a body that isn't JSON) share `attempts`;
    before attempt n+1 wait uniform[d/2, d], d = min(8, 0.5 * 2**(n-1)).
    429: wait Retry-After (seconds or HTTP date vs Date header; 1s if missing). Doesn't use up `attempts`;
    ApiError after `max_429` 429s in a row. Any other status: ApiError right away (check e.status, e.g. 401)."""
    kwargs.setdefault("timeout", 10)
    failures, in_a_row = 0, 0
    while True:
        r, problem = None, ""
        try:
            r = http.request(method, url, **kwargs)
        except httpx.TransportError as e:
            problem = type(e).__name__
        if r is not None and r.status_code == 429:
            in_a_row += 1
            if in_a_row >= max_429:
                raise ApiError(429, url, f"{in_a_row} rate limits in a row")
            value = r.headers.get("Retry-After", "").strip()
            wait = 1.0
            if value.isdigit():
                wait = float(value)
            elif value:
                try:
                    base = parsedate_to_datetime(r.headers["Date"]).timestamp() if "Date" in r.headers else time.time()
                    wait = max(0.0, parsedate_to_datetime(value).timestamp() - base)
                except (TypeError, ValueError, IndexError):
                    pass
            sleep(wait)
            continue
        in_a_row = 0
        if r is not None and 200 <= r.status_code < 300:
            try:
                return r.json()
            except ValueError:
                problem = "invalid JSON body"
        elif r is not None and r.status_code not in transient:
            raise ApiError(r.status_code, url, r.text[:200])
        failures += 1
        if failures >= attempts:
            raise ApiError(r.status_code if r is not None else None, url, problem or "transient failure")
        d = min(8.0, 0.5 * 2 ** (failures - 1))
        sleep(d / 2 + (d / 2) * rng())
```

### Step 11: Combine it with the token refresh

```python
def api_get(path, **params):
    for retry_401 in (True, False):
        token = get_token()                                  # token_provider snippet, part 9
        try:
            return get_json_with_retries(http, "GET", path, params=params,
                                         headers={"Authorization": f"Bearer {token}"})
        except ApiError as e:
            if e.status == 401 and retry_401:
                get_token(invalid=token)                     # refresh once, then retry once
                continue
            raise
```

---

## Part 3: Async without the classic mistakes

### Step 12: Never `time.sleep` in async code

`time.sleep(1)` inside a coroutine blocks the whole event loop: every other request stops too. Use `await asyncio.sleep(1)`. And every coroutine call needs its `await`; a missing one just creates a coroutine object that never runs.

### Step 13: The semaphore must wrap the awaited call

Creating `asyncio.Semaphore(5)` does nothing unless `async with sem:` surrounds the actual `await client.get(...)`. Acquiring it somewhere else, or not at all, means unlimited concurrency.

### Step 14: Don't let one failure hide the others

By default, `asyncio.gather` raises the first exception, and you lose every other result. `return_exceptions=True` puts the exception object in that item's slot, so you can report exactly which items failed.

### The complete snippet

```python
import asyncio

import httpx


async def arequest_with_retries(client: httpx.AsyncClient, method: str, url: str, *,
                                retries: int = 3, backoff: float = 0.5, **kwargs):
    """Async request_with_retries. Uses `await asyncio.sleep`: time.sleep would freeze every coroutine.
    Returns the first non-retryable Response (2xx or other 4xx), or None after all attempts failed."""
    kwargs.setdefault("timeout", 10)
    for attempt in range(retries + 1):
        if attempt:
            await asyncio.sleep(backoff * 2 ** (attempt - 1))
        try:
            r = await client.request(method, url, **kwargs)
        except httpx.TransportError:
            continue
        if r.status_code != 429 and r.status_code < 500:
            return r
    return None


async def gather_bounded_safe(fn, items, limit: int = 5) -> list:
    """await fn(item) for every item, at most `limit` at once, results in input order.
    A failure becomes the exception object in its slot (check isinstance(x, Exception)) instead of
    discarding everyone else's results."""
    sem = asyncio.Semaphore(limit)

    async def run(item):
        async with sem:                     # the semaphore must wrap the awaited call itself
            return await fn(item)

    return await asyncio.gather(*(run(i) for i in items), return_exceptions=True)
```

```python
async with httpx.AsyncClient(base_url=BASE) as client:
    results = await gather_bounded_safe(
        lambda i: arequest_with_retries(client, "GET", f"/items/{i}"), ids, limit=5)
failed = [i for i, r in zip(ids, results) if isinstance(r, Exception) or r is None]
```

---

## Testing

```python
def test_schedule_respects_retry_after_and_dead_letters():
    d = {"status": "pending"}
    record_attempt(d, now=0, response=httpx.Response(429, headers={"Retry-After": "500"}))
    assert d["next_attempt_at"] == 500 and due([d], 499) == []
    for _ in range(4):
        record_attempt(d, now=600, response=httpx.Response(503))
    assert d["status"] == "dead" and d["attempts"] == 5


def test_crawl_budgets():
    sleeps = []
    client, stats = fake_http([500, "timeout", httpx.Response(200, content=b'{"trunc'), {"ok": 1}])
    assert get_json_with_retries(client, "GET", "http://x/a", sleep=sleeps.append, rng=lambda: 1.0) == {"ok": 1}
    assert sleeps == [0.5, 1.0, 2.0]

    client, stats = fake_http([httpx.Response(429)])          # 429 forever
    with pytest.raises(ApiError):
        get_json_with_retries(client, "GET", "http://x/b", sleep=lambda s: None)
    assert len(stats["requests"]) == 10
```

---

## Recap

1. **Schedule retries** with `next_attempt_at` and never sleep in a dispatcher. Classify each attempt, back off with jitter and a cap, honor `Retry-After` exactly, and dead-letter after N attempts.
2. **Crawls:** transient failures (including broken 200 bodies) share one budget, 429s don't use it but are capped in a row, and everything else raises with its status.
3. **Async:** `await asyncio.sleep`, wrap the awaited call in the semaphore, and gather with `return_exceptions=True`.
