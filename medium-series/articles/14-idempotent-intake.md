# Idempotency Keys, Per-Tenant Rate Limits, and SQLite Under Load: A Step-by-Step Python Guide

### Make a POST endpoint safe to retry, fair across tenants, and correct with 20 threads hitting it at once

Clients retry. A POST that timed out on the client may have succeeded on the server, so the retry creates a duplicate. One tenant's batch job floods the API and slows everyone else down. Then you add a database, and under parallel requests it starts throwing `database is locked`.

This tutorial builds four standalone snippets that fix those problems, plus the test clock that makes them testable:

1. `fake_clock()`: test time-based logic without sleeping
2. `run_idempotent()`: idempotency keys for your own endpoints
3. `make_bucket_store()`: a token bucket per tenant
4. `get_conn()` and `write_tx()`: SQLite that stays correct across threads and restarts

**What you need:** Python 3.9+, `pip install fastapi`.

---

## Step 1: Inject the clock

Expiry, rate limits and leases all depend on time. If your code calls `time.time()` directly, tests have to `sleep(86400)` to check a 24-hour expiry. Instead, accept a `clock` and pass a fake one in tests:

```python
from types import SimpleNamespace


def fake_clock(start: float = 1_700_000_000.0):
    """clock.time(), clock.monotonic(), clock.sleep(s) (returns instantly), clock.advance(s), clock.sleeps.
    Inject it wherever code would call time.time() / time.monotonic() / time.sleep()."""
    state = {"now": float(start)}
    sleeps = []

    def advance(seconds: float) -> None:
        state["now"] += seconds

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        advance(seconds)

    return SimpleNamespace(time=lambda: state["now"], monotonic=lambda: state["now"],
                           sleep=sleep, advance=advance, sleeps=sleeps)
```

```python
clock = fake_clock()
app = create_app(storage_dir, clock=clock)
clock.advance(86_400)            # a day passes instantly
```

---

## Part 1: Idempotency keys

### Step 2: The contract

The client sends `Idempotency-Key: <unique string>` with a POST. The server promises:

- **Same key, same body:** return the *original* response again (a replay), and don't create a second resource.
- **Same key, different body:** **409**. That's a client bug.
- **Same key while the first request is still running:** **409** ("in progress"), so concurrent retries can't both create.
- **The first attempt failed** (an exception, or a 429): store nothing, so a retry can succeed.

### Step 3: Fingerprint the body

To decide "same body", hash a *canonical* JSON form, with sorted keys and no extra whitespace. Then `{"a":1,"b":2}` and `{"b": 2, "a": 1}` match.

### Step 4: Reserve the key before doing the work

The race to avoid: two identical requests arrive together, both see "no record", and both create. The fix is to insert an `in_progress` record **under a lock before calling `create()`**. The second request then sees the record and gets a 409.

### Step 5: Scope keys per tenant, and expire them

Key `"abc"` from tenant A and key `"abc"` from tenant B are different keys, so the record key is `(tenant, key)`. Records expire after a TTL (24 hours is common), after which the key can be used again.

### The complete snippet

```python
import hashlib
import json
import re
import threading
import time

KEY_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
RECORDS: dict = {}               # (scope, key) -> record; persist it (atomically) if it must survive restarts
LOCK = threading.Lock()


def fingerprint(body) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run_idempotent(scope: str, key, body, create, ttl: float = 86_400, clock=time.time,
                   records: dict = RECORDS, lock=LOCK):
    """Run create() -> (status, response_body) at most once per (scope, key). Returns (status, body, replayed).

    key None          -> just create()
    key malformed     -> ValueError (map to 400)
    seen, same body   -> the stored response, replayed=True (send header Idempotent-Replayed: true)
    seen, other body  -> (409, ...)
    first still running (concurrent retry) -> (409, ...)
    create() raises or returns non-2xx -> nothing stored; the key can be retried
    record older than ttl -> ignored; the key is reusable
    """
    if key is None:
        status, resp = create()
        return status, resp, False
    if not KEY_RE.fullmatch(key):
        raise ValueError("invalid Idempotency-Key")
    fp, rk = fingerprint(body), (scope, key)
    with lock:
        rec = records.get(rk)
        if rec is not None and clock() >= rec["created_at"] + ttl:
            records.pop(rk)
            rec = None
        if rec is not None:
            if rec["fingerprint"] != fp:
                return 409, {"detail": "Idempotency-Key was used with a different request"}, False
            if rec["state"] == "in_progress":
                return 409, {"detail": "a request with this key is in progress"}, False
            return rec["status"], rec["body"], True
        records[rk] = {"fingerprint": fp, "state": "in_progress", "created_at": clock()}
    try:
        status, resp = create()
    except BaseException:
        with lock:
            records.pop(rk, None)
        raise
    with lock:
        if 200 <= status < 300:
            records[rk].update(state="done", status=status, body=resp)
        else:
            records.pop(rk, None)
    return status, resp, False
```

### Step 6: Wire it into FastAPI

```python
@app.post("/tasks", status_code=201)
def create_task(body: TaskIn, response: Response, x_tenant_id: str = Header(...),
                idempotency_key: str = Header(None)):
    try:
        status, data, replayed = run_idempotent(x_tenant_id, idempotency_key, body.dict(),
                                                lambda: (201, save_task(x_tenant_id, body)))
    except ValueError:
        raise HTTPException(400, "invalid Idempotency-Key")
    if status == 409:
        raise HTTPException(409, data["detail"])
    if replayed:
        response.headers["Idempotent-Replayed"] = "true"
    return data
```

**Order of checks** matters, and specs usually define it: tenant header (400/403), key format (400), body (422), idempotency (replay/409), rate limit (429), and only then create (201). A replay costs no rate-limit token.

**Restarts:** `RECORDS` is a plain dict. To survive restarts, save it with an atomic write after every change, or keep the records in a SQLite table (Part 3).

---

## Part 2: A token bucket per tenant

### Step 7: Server side means non-blocking

The client-side limiter in part 9 of this series *waits*. A server can't make a request wait, so it *rejects* with 429 and tells the client how long to wait.

### Step 8: Refill continuously, fractions included

After 0.5 seconds at 1 token/s there's half a token. Store `(tokens, last_time)` per key, and on every request add `elapsed * refill_per_s`, capped at `burst`.

### Step 9: `Retry-After` rounds up and is at least 1

With 0.875 tokens and a refill rate of 0.25 per second, the next whole token arrives in 0.5 s, so the header must say `1`, not `0`. Round up, with a floor of 1. The snippet rounds to 9 decimal places before taking the ceiling, so floating-point noise like `3.0000000000000004` doesn't become 4.

### Step 10: One lock for concurrency

Ten simultaneous requests from a tenant with `burst=5` must produce exactly five 201s and five 429s. A single lock around the read-modify-write guarantees that.

### The complete snippet

```python
import math
import threading
import time


def make_bucket_store(clock=time.monotonic):
    """take(key, burst, refill_per_s, cost=1) -> (allowed, retry_after_s).
    Each key has its own bucket: starts full, refills continuously (fractional tokens count), never above burst.
    retry_after_s = seconds until `cost` tokens exist, rounded UP, at least 1 (0 when allowed). Thread-safe."""
    buckets: dict = {}
    lock = threading.Lock()

    def take(key, burst: float, refill_per_s: float, cost: float = 1.0):
        with lock:
            now = clock()
            tokens, last = buckets.get(key, (float(burst), now))
            tokens = min(float(burst), tokens + (now - last) * refill_per_s)
            if tokens >= cost:
                buckets[key] = (tokens - cost, now)
                return True, 0
            buckets[key] = (tokens, now)
            return False, max(1, math.ceil(round((cost - tokens) / refill_per_s, 9)))

    return take
```

```python
take = make_bucket_store(clock.time)
ok, wait = take(tenant_id, plan["burst"], plan["refill_per_s"])
if not ok:
    raise HTTPException(429, "rate limit exceeded", headers={"Retry-After": str(wait)})
```

---

## Part 3: SQLite that survives many threads

### Step 11: One connection per thread

A `sqlite3.Connection` must not be shared between threads. FastAPI runs `def` endpoints in a thread pool, and tests often fire requests from several threads. Keep connections in `threading.local()`.

### Step 12: WAL mode and a busy timeout

- **`journal_mode=WAL`** lets reads continue while a write is in progress.
- **`busy_timeout`** makes a writer *wait* for the lock instead of failing immediately with `database is locked`.

### Step 13: `BEGIN IMMEDIATE` for read-then-write

"Find the oldest pending task, then lease it" is two statements. With a plain `BEGIN`, two threads can both read the same row before either writes. `BEGIN IMMEDIATE` takes the write lock **before** the read, so the whole claim is atomic, across threads and across processes.

### The complete snippet

```python
import sqlite3
import threading
from contextlib import contextmanager

_local = threading.local()


def get_conn(path: str) -> sqlite3.Connection:
    """One connection per thread per file (connections must not be shared across threads).
    WAL lets readers run during writes; busy_timeout makes writers wait instead of failing."""
    conns = getattr(_local, "conns", None)
    if conns is None:
        conns = _local.conns = {}
    conn = conns.get(path)
    if conn is None:
        conn = sqlite3.connect(path, timeout=30, isolation_level=None)    # we control transactions
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conns[path] = conn
    return conn


@contextmanager
def write_tx(path: str):
    """BEGIN IMMEDIATE takes the write lock up front, so read-then-write logic (claim the oldest task,
    check-then-insert) is atomic across threads AND processes. Commits on success, rolls back on error."""
    conn = get_conn(path)
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
```

```python
with write_tx(DB) as db:
    row = db.execute("SELECT id FROM tasks WHERE state = 'pending' ORDER BY seq LIMIT 1").fetchone()
    if row:
        db.execute("UPDATE tasks SET state = 'leased', annotator = ?, expires_at = ? WHERE id = ?",
                   (annotator, now + lease_s, row["id"]))
```

Durability comes free: a new app started over the same file sees every task, lease and idempotency record.

---

## Testing

```python
def test_idempotent_replay_and_conflict():
    clock, records, lock = fake_clock(0), {}, threading.Lock()
    kw = dict(clock=clock.time, records=records, lock=lock)
    create = lambda: (201, {"id": "t1"})
    assert run_idempotent("acme", "k1", {"a": 1}, create, **kw) == (201, {"id": "t1"}, False)
    assert run_idempotent("acme", "k1", {"a": 1}, create, **kw)[2] is True       # replay
    assert run_idempotent("acme", "k1", {"a": 2}, create, **kw)[0] == 409        # different body
    clock.advance(86_400)
    assert run_idempotent("acme", "k1", {"a": 2}, create, **kw)[0] == 201        # expired


def test_retry_after_rounds_up():
    clock = fake_clock(0)
    take = make_bucket_store(clock.time)
    take("a", 2, 0.25); take("a", 2, 0.25)
    assert take("a", 2, 0.25) == (False, 4)
    clock.advance(3.5)                                                          # 0.875 tokens
    assert take("a", 2, 0.25) == (False, 1)


def test_twenty_threads_claim_each_task_once(tmp_path):
    ...  # 5 pending rows, 20 threads each run the claim above -> 5 distinct ids claimed
```

---

## Recap

1. **Inject a clock** so time-based rules can be tested instantly.
2. **Idempotency keys:** fingerprint the body, reserve the key *before* working, replay on a match, return 409 on a mismatch or while in progress, never store failures, and expire records.
3. **Per-tenant token bucket:** refill continuously, reject with 429, round `Retry-After` up to at least 1, and use one lock.
4. **SQLite under load:** a connection per thread, WAL plus `busy_timeout`, and `BEGIN IMMEDIATE` around read-then-write.
