# Signed Webhooks in Python, Step by Step: HMAC, Idempotency Keys, and Retries

### Build the sender and the receiver, and see why each line is there

A webhook is just a POST from your server to someone else's. What makes it tricky is the network. A request can time out *after* the receiver already processed it. Retries cause duplicates. Anyone who discovers the URL can send fake events.

In this tutorial we'll build both sides:

- **Sender:** `send_webhook()` signs the body, adds an idempotency key, and retries safely.
- **Receiver:** `verify_signature()` rejects forgeries, and `insert_once()` drops duplicates.

**What you need:** Python 3.9+, `pip install httpx fastapi uvicorn`.

---

## The contract we're implementing

```
POST https://customer.example.com/hooks
Content-Type: application/json
Idempotency-Key: P01
X-Signature: sha256=<hex HMAC-SHA256 of the exact body bytes, keyed with a shared secret>

{"task_id":"P01","label":"spam"}
```

---

## Part 1: The sender

### Step 1: The naive version

```python
httpx.post(url, json={"task_id": "P01", "label": "spam"})
```

Three problems:

- The receiver can't tell whether the request really came from us.
- If it times out, we don't know whether it arrived.
- If we retry, the receiver might process it twice.

### Step 2: Serialize once, so you sign the exact bytes you send

The signature is computed over **bytes**. If you sign `json.dumps(payload)` and then call `httpx.post(url, json=payload)`, httpx serializes the payload *again*, possibly with different spacing, and the signature no longer matches.

So serialize once, and send those exact bytes with `content=`:

```python
body = json.dumps(payload, separators=(",", ":")).encode()
```

### Step 3: Sign with HMAC-SHA256

HMAC combines a shared secret with the body. Only someone who knows the secret can produce a matching signature:

```python
import hashlib, hmac

signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
```

The `sha256=` prefix tells the receiver which algorithm you used, so you can change algorithms later without breaking anyone.

### Step 4: Add an idempotency key

Give every event a stable ID and send it as `Idempotency-Key`. The important rule: **every retry of the same event uses the same key.** That's how the receiver recognizes a retry as a duplicate.

```python
headers = {
    "Content-Type": "application/json",
    "Idempotency-Key": idempotency_key,
    "X-Signature": signature,
}
```

### Step 5: Retry only what's temporary

- **Any 2xx means delivered.** Receivers use 200, 202 and 204 more or less at random.
- **429, 5xx, timeouts and connection errors are temporary:** retry with backoff.
- **400 and 401 are permanent.** A bad signature won't fix itself on a second try, so stop.

### The complete sender

```python
import hashlib
import hmac
import json
import time

import httpx


def send_webhook(url: str, secret: str, payload: dict, idempotency_key: str, *,
                 retries: int = 2, backoff: float = 0.2, timeout: float = 5, client=None) -> bool:
    """POST signed JSON. Any 2xx -> True. Retries 429/5xx/network errors with the SAME key.
    Header: X-Signature: sha256=<hex HMAC-SHA256 of the exact body bytes>."""
    body = json.dumps(payload, separators=(",", ":")).encode()      # sign exactly what we send
    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotency_key,
        "X-Signature": "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest(),
    }
    http = client or httpx.Client()
    try:
        for attempt in range(retries + 1):
            if attempt:
                time.sleep(backoff * 2 ** (attempt - 1))
            try:
                r = http.post(url, content=body, headers=headers, timeout=timeout)
            except httpx.TransportError:
                continue
            if r.is_success:
                return True
            if r.status_code != 429 and r.status_code < 500:
                return False                      # 400/401/...: retrying won't help
        return False
    finally:
        if client is None:
            http.close()
```

Send many events with a bounded thread pool, so you don't open 200 connections to a customer's small server:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as pool:
    delivered = list(pool.map(
        lambda t: send_webhook(url, secret, {"task_id": t["id"], "label": t["label"]}, t["id"]),
        tasks))
```

---

## Part 2: The receiver

### Step 6: Verify against the raw bytes

The receiver recomputes the HMAC over the **raw** request body. If you call `await request.json()` and serialize it again, the bytes may differ and every signature will fail.

Compare with `hmac.compare_digest`, not `==`. A normal string comparison stops at the first different character, so its timing can leak how much of a guess was correct. `compare_digest` always takes the same time.

```python
import hashlib
import hmac


def verify_signature(secret: str, body: bytes, header, prefix: str = "sha256=") -> bool:
    """Compare against the RAW request bytes (await request.body()), in constant time."""
    expected = prefix + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header or "")
```

### Step 7: Drop duplicates with a database constraint

An in-memory `set()` of seen IDs is lost on restart and isn't shared between workers. Let the database enforce uniqueness instead. `INSERT OR IGNORE` on a primary key is atomic, so even two simultaneous retries can't both get through:

```python
import sqlite3


def insert_once(db_path: str, event_id: str, payload: str) -> bool:
    """True if this event is new, False if it was already stored. Atomic even under concurrent retries."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, payload TEXT, "
                     "status TEXT DEFAULT 'pending')")
        cur = conn.execute("INSERT OR IGNORE INTO events (id, payload) VALUES (?, ?)", (event_id, payload))
        return cur.rowcount == 1
```

In Postgres, the equivalent is `INSERT ... ON CONFLICT DO NOTHING`.

### Step 8: Store first, answer second, work last

Put it together in the endpoint. The order of these steps matters:

```python
import json, os
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

app = FastAPI()

@app.post("/hooks")
async def receive(request: Request, background: BackgroundTasks,
                  x_signature: str = Header(None), idempotency_key: str = Header()):
    body = await request.body()                                      # 1. raw bytes
    if not verify_signature(os.environ["WEBHOOK_SECRET"], body, x_signature):
        raise HTTPException(401, "bad signature")                    # 2. reject forgeries
    if not insert_once("events.db", idempotency_key, body.decode()):
        return {"status": "duplicate"}                               # 3. still a 2xx!
    background.add_task(process, idempotency_key)                    # 4. slow work later
    return {"status": "accepted"}                                    # 5. answer fast
```

- **A duplicate still gets a 2xx.** If you return an error, the sender keeps retrying something you already have.
- **The event is stored before you answer.** Once you return 200, the sender forgets the event. The stored row is what survives if you crash a second later.
- **Slow work runs after the response.** If you do it before answering, the sender may time out, assume failure, and retry.

---

## Step 9: Test both sides together

Using the `fake_http` helper from part 1 of this series:

```python
def test_sender_signs_and_retries_with_same_key():
    client, stats = fake_http([503, 204])
    assert send_webhook("http://x", "s3cret", {"a": 1}, "k1", backoff=0, client=client)
    reqs = stats["requests"]
    assert {r.headers["Idempotency-Key"] for r in reqs} == {"k1"}             # same key on retry
    assert verify_signature("s3cret", reqs[0].content, reqs[0].headers["X-Signature"])
    assert not verify_signature("s3cret", reqs[0].content + b" ", reqs[0].headers["X-Signature"])


def test_permanent_failure_is_not_retried():
    client, stats = fake_http([401])
    assert not send_webhook("http://x", "s", {}, "k", backoff=0, client=client)
    assert len(stats["requests"]) == 1


def test_receiver_dedupes(tmp_path):
    db = str(tmp_path / "e.db")
    assert insert_once(db, "e1", "{}") is True
    assert insert_once(db, "e1", "{}") is False
```

---

## Two questions you'll get asked

**"The request timed out, but the customer actually got it. Now what?"**
You mark it failed and retry with the **same idempotency key**. The receiver's `insert_once` sees the key, returns 200, and does nothing. Delivery is *at least once*; processing is *effectively once*.

**"The customer's endpoint is down for six hours."**
Three retries over one second won't get you through that. Store each outbound event in an `outbox` table with `attempts` and `next_attempt_at` columns. A worker retries with growing gaps (1 min, 5 min, 30 min, 2 h…) for about a day, then marks the event `failed` and offers a "redeliver" button. Because of the idempotency key, redelivery is always safe.

---

## Recap

1. **Serialize once** and sign those exact bytes with HMAC-SHA256.
2. **Keep the idempotency key identical** across retries.
3. **Retry only** 429s, 5xx errors and network errors, and treat any 2xx as delivered.
4. **Verify against the raw body** using `compare_digest`.
5. **Dedupe with a database constraint,** store before you answer, and do the slow work later.

*Next: processing an untrusted CSV safely in FastAPI.*
