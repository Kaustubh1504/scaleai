# Building Well-Behaved API Clients in Python: Auth Tokens, Rate Limits, and Caching, Step by Step

### Three small snippets for when someone else's API has rules

When your backend calls an upstream API, that API sets the rules. Tokens expire every hour. You're allowed 10 requests per second. And the same customer gets looked up 200 times in one batch.

In this tutorial we'll build three standalone snippets:

1. **`make_token_getter` + `call_with_token`:** cache an auth token, refresh it before expiry, and recover from a 401.
2. **`make_rate_limiter` + `retry_after_seconds`:** stay under a request rate, and respect `Retry-After`.
3. **`make_cached`:** a TTL cache where ten simultaneous requests for the same key make one upstream call.

**What you need:** Python 3.9+, `pip install httpx`.

---

## Part 1: Auth tokens

### Step 1: The naive version

```python
def get_projects():
    token = httpx.post(f"{BASE}/oauth/token", json=creds).json()["access_token"]
    return httpx.get(f"{BASE}/projects", headers={"Authorization": f"Bearer {token}"})
```

This fetches a new token on *every* call. That doubles your traffic, and many token endpoints are themselves rate-limited.

### Step 2: Cache the token until shortly before it expires

Token responses usually include `expires_in` (in seconds). Store the token with its expiry time, and reuse it until `refresh_margin` seconds before it expires. The margin covers clock skew and requests that are still in flight.

### Step 3: Recover from an early 401

Tokens can be revoked or expire early. When a call returns 401, refresh **once** and retry **once**. Never loop: if a fresh token also gets a 401, your credentials are wrong.

### Step 4: Don't refresh ten times at once

If ten threads get a 401 at the same moment, you want one refresh, not ten. Each thread tells the getter *which* token failed (`invalid=token`). The getter refreshes only if that token is still the current one; otherwise another thread already refreshed it, and the new token is returned. A lock makes the check-and-refresh atomic.

### The complete snippet

```python
import threading
import time


def make_token_getter(fetch_token, refresh_margin: float = 30.0, clock=time.time):
    """fetch_token() -> (token, expires_in_seconds). Returns get_token(invalid=None):
    cached until `refresh_margin` s before expiry; pass the token that got a 401 as `invalid`
    to force a refresh (only one thread refreshes; others reuse the new token)."""
    state = {"token": None, "expires_at": 0.0}
    lock = threading.Lock()

    def get_token(invalid=None):
        with lock:
            stale = state["token"] is None or clock() >= state["expires_at"] - refresh_margin
            if stale or (invalid is not None and invalid == state["token"]):
                token, expires_in = fetch_token()
                state["token"], state["expires_at"] = token, clock() + float(expires_in)
            return state["token"]

    return get_token


def call_with_token(get_token, send):
    """send(token) -> httpx.Response. On 401: refresh the token and retry once."""
    token = get_token()
    r = send(token)
    if r.status_code == 401:
        r = send(get_token(invalid=token))
    return r
```

```python
def fetch_token():
    body = httpx.post(f"{BASE}/oauth/token", json={"client_id": cid, "client_secret": secret}).json()
    return body["access_token"], body["expires_in"]

get_token = make_token_getter(fetch_token)

r = call_with_token(get_token, lambda t: httpx.get(f"{BASE}/projects",
                                                  headers={"Authorization": f"Bearer {t}"}))
```

---

## Part 2: Rate limiting your own calls

### Step 5: Why retrying 429s isn't enough

If you send 50 requests per second to an API that allows 10, you get 40 errors per second, and the retries make it worse. Pace yourself *before* sending.

### Step 6: A token bucket that waits instead of rejecting

The server-side rate limiter from part 5 of this series *rejected* requests. On the client side, we *wait* until we're allowed to send. The bucket refills at `rate` tokens per second; each request takes a token; an empty bucket means sleeping until the next one arrives.

### Step 7: Share one limiter across all workers

The limit applies to your whole process, not to each thread. Create one limiter and call `acquire()` before every request, from every worker. A lock keeps the bucket consistent.

### Step 8: Respect `Retry-After`

When you still get a 429, the server often tells you how long to wait. The header can be a number of seconds or an HTTP date. Cap the wait, so a broken header can't stall you for an hour.

### The complete snippet

```python
import threading
import time
from email.utils import parsedate_to_datetime


def make_rate_limiter(rate: float, burst: int = 1, clock=time.monotonic, sleep=time.sleep):
    """Returns acquire(): blocks until one more request is allowed (`rate` per second, bursts up to `burst`).
    Thread-safe: share one limiter across all workers hitting the same API."""
    state = {"tokens": float(burst), "last": clock()}
    lock = threading.Lock()

    def acquire():
        while True:
            with lock:
                now = clock()
                state["tokens"] = min(burst, state["tokens"] + (now - state["last"]) * rate)
                state["last"] = now
                if state["tokens"] >= 1:
                    state["tokens"] -= 1
                    return
                wait = (1 - state["tokens"]) / rate
            sleep(wait)

    return acquire


def retry_after_seconds(response, default: float = 1.0, cap: float = 60.0) -> float:
    """Seconds to wait from a Retry-After header (number of seconds or an HTTP date)."""
    value = response.headers.get("Retry-After")
    if not value:
        return default
    try:
        return min(cap, max(0.0, float(value)))
    except ValueError:
        pass
    try:
        return min(cap, max(0.0, parsedate_to_datetime(value).timestamp() - time.time()))
    except (TypeError, ValueError):
        return default
```

```python
limit = make_rate_limiter(rate=10, burst=10)

def fetch(item_id):
    for attempt in range(4):
        limit()
        r = httpx.get(f"{BASE}/items/{item_id}")
        if r.status_code != 429:
            return r
        time.sleep(retry_after_seconds(r))
    return r
```

The `clock` and `sleep` parameters let tests check the pacing without waiting in real time.

---

## Part 3: A TTL cache that coalesces requests

### Step 9: Cache with an expiry

Customer records, exchange rates and config change slowly. Remember each result for `ttl` seconds, using `time.monotonic()` so changes to the system clock can't affect expiry.

### Step 10: Prevent the stampede

Plain caches have a gap. Ten threads miss the same key at the same moment, and all ten call the upstream. The fix is **request coalescing**: the first thread (the "leader") makes the call, and the others wait on an `Event` and share its result.

### Step 11: Never cache failures

If the upstream errors, the leader re-raises, the waiting threads get the same error, and *nothing is stored*, so the next request tries again. `None` (for example "not found") is cached only if you ask for it.

### Step 12: Count hits and misses

Return a `stats` dictionary. Exposing hits, misses and coalesced calls on a `/metrics` endpoint is how you show the cache is doing its job.

### The complete snippet

```python
import threading
import time


def make_cached(fn, ttl: float = 60.0, cache_none: bool = False, clock=time.monotonic):
    """Returns (cached, stats). cached(key) -> fn(key), remembered for `ttl` seconds.
    Concurrent misses for the same key make ONE call; the others wait and share its result or error.
    Errors are never cached; None is cached only if cache_none."""
    entries = {}                                          # key -> (value, expires_at)
    inflight = {}                                         # key -> {"event", "value"/"error"}
    lock = threading.Lock()
    stats = {"hits": 0, "misses": 0, "calls": 0, "coalesced": 0}

    def cached(key):
        with lock:
            hit = entries.get(key)
            if hit is not None and hit[1] > clock():
                stats["hits"] += 1
                return hit[0]
            slot = inflight.get(key)
            leader = slot is None
            if leader:
                slot = inflight[key] = {"event": threading.Event()}
                stats["misses"] += 1
                stats["calls"] += 1
            else:
                stats["coalesced"] += 1
        if not leader:
            slot["event"].wait()
            if "error" in slot:
                raise slot["error"]
            return slot["value"]
        try:
            value = fn(key)
            slot["value"] = value
            with lock:
                if value is not None or cache_none:
                    entries[key] = (value, clock() + ttl)
            return value
        except Exception as e:
            slot["error"] = e
            raise
        finally:
            with lock:
                inflight.pop(key, None)
            slot["event"].set()

    return cached, stats
```

```python
get_customer, cache_stats = make_cached(lambda cid: fetch_customer(cid), ttl=300)
customers = bounded_map(lambda t: get_customer(t["customer_id"]), tickets, 5)
```

---

## Testing

```python
def test_token_refreshes_once_on_401():
    issued = []
    def fetch():
        issued.append(f"tok{len(issued)}")
        return issued[-1], 3600
    get = make_token_getter(fetch)
    sent = []
    def send(tok):
        sent.append(tok)
        return httpx.Response(401 if tok == "tok0" else 200)
    assert call_with_token(get, send).status_code == 200
    assert sent == ["tok0", "tok1"]


def test_ten_threads_one_call():
    calls = []
    def slow(k):
        calls.append(k)
        time.sleep(0.05)
        return k * 2
    cached, stats = make_cached(slow, ttl=10)
    threads = [threading.Thread(target=cached, args=(1,)) for _ in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert calls == [1] and stats["coalesced"] == 9
```

---

## Recap

1. **Cache tokens** until just before expiry. On a 401, refresh once and retry once, and only the thread holding the stale token refreshes.
2. **Pace your requests** with a shared token bucket, and honor `Retry-After`.
3. **Cache slow lookups with a TTL**, coalesce concurrent misses into one call, and never cache errors.
