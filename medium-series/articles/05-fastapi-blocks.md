# Four FastAPI Building Blocks, Step by Step: Request IDs, Rate Limits, Background Jobs, and Optimistic Locking

### Each one is a single function you can add to any app

These four problems only show up once real traffic arrives:

- an error you can't trace through the logs,
- one client flooding the API,
- requests that take too long to answer while the client waits,
- two users silently overwriting each other's edits.

We'll fix each one with a single function. Each section starts from the problem, builds the fix step by step, and ends with the complete code.

**What you need:** Python 3.9+, `pip install fastapi uvicorn`.

```python
from fastapi import FastAPI
app = FastAPI()
```

---

## 1. Request IDs: trace any request through your logs

### The problem

A user reports "it failed at 3:02 PM." Your logs have 4,000 lines from that minute. Which ones belong to that request?

### Step 1: Give every request an ID

Add a middleware that reuses the `X-Request-ID` header if the caller sent one (so the same ID follows a request across services), or generates a new one otherwise. Return it in the response, so users can quote it in bug reports.

### Step 2: Make the ID available everywhere, without passing it around

A global variable would be shared by every concurrent request. Use a `ContextVar` instead: each request gets its own value, even with hundreds running at once.

### Step 3: Stamp it on every log line automatically

Rather than adding the ID to each `log.info(...)` call by hand, add a logging **filter** that copies it onto every record. Then the formatter can print it.

### The complete function

```python
import logging
import uuid
from contextvars import ContextVar

request_id = ContextVar("request_id", default="-")


def add_request_id(app, logger_name: str = "app") -> logging.Logger:
    """Adds X-Request-ID middleware and returns a logger whose lines include the id."""
    class Filter(logging.Filter):
        def filter(self, record):
            record.request_id = request_id.get()
            return True

    log = logging.getLogger(logger_name)
    handler = logging.StreamHandler()
    handler.addFilter(Filter())
    handler.setFormatter(logging.Formatter("%(asctime)s [%(request_id)s] %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)

    @app.middleware("http")
    async def middleware(request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id.reset(token)
        response.headers["X-Request-ID"] = rid
        return response

    return log
```

```python
log = add_request_id(app)

@app.get("/orders")
def list_orders():
    log.info("listing orders")      # 2024-05-01 15:02:11 [3f2a9c...] INFO listing orders
    return []
```

---

## 2. Rate limiting: one client shouldn't take everyone down

### Step 1: Choose an algorithm

A **token bucket** allows short bursts but caps the long-run rate. Each client has a bucket holding up to `burst` tokens. It refills at `rate` tokens per second, and each request spends one token. An empty bucket means 429.

### Step 2: Refill lazily

You don't need a timer. When a request arrives, add the tokens earned since the client's last request:

```python
tokens = min(burst, tokens + (now - last) * rate)
```

Use `time.monotonic()`, not `time.time()`. The wall clock can jump backwards when the system syncs its time.

### Step 3: Tell the client when to come back

On a 429, compute how long until one token is available, and send it in `Retry-After`. Well-behaved clients will wait exactly that long.

### The complete function

```python
import math
import time

from fastapi.responses import JSONResponse


def add_rate_limit(app, rate: float = 5, burst: int = 10, key=None):
    """429 + Retry-After when a client exceeds `rate` req/s (bursts up to `burst`). Per process."""
    buckets: dict[str, tuple[float, float]] = {}
    key = key or (lambda req: req.headers.get("X-API-Key") or req.client.host)

    def allow(k: str) -> tuple[bool, float]:
        now = time.monotonic()
        tokens, last = buckets.get(k, (burst, now))
        tokens = min(burst, tokens + (now - last) * rate)
        if tokens < 1:
            buckets[k] = (tokens, now)
            return False, (1 - tokens) / rate
        buckets[k] = (tokens - 1, now)
        return True, 0.0

    @app.middleware("http")
    async def middleware(request, call_next):
        ok, wait = allow(key(request))
        if not ok:
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429,
                                headers={"Retry-After": str(math.ceil(wait))})
        return await call_next(request)

    return allow
```

```python
add_rate_limit(app, rate=5, burst=10)                                          # by API key or IP
add_rate_limit(app, rate=1, burst=3, key=lambda req: req.headers.get("X-User-ID", "anon"))
```

**Limits to know about:**

- The buckets live in one process. With four workers, each client effectively gets 4× the limit. For a shared limit, keep the buckets in Redis.
- The dict grows by one entry per client. Evict idle entries in long-running services.

---

## 3. Background jobs: answer now, work later

### The problem

A request that processes 10,000 rows takes minutes. Clients, proxies and load balancers will time out long before it finishes.

### Step 1: Accept the job immediately

Return `202 Accepted` with a job ID and a URL the client can poll.

### Step 2: Run the work after the response

FastAPI's `BackgroundTasks` runs a function once the response has been sent.

### Step 3: Always record the outcome

If the work raises and you don't catch it, the job stays `running` forever, and clients poll forever. Wrap it, and store either the result or the error.

### The complete function

```python
import uuid

from fastapi import BackgroundTasks, HTTPException

JOBS: dict[str, dict] = {}


def start_job(background_tasks: BackgroundTasks, fn, *args) -> dict:
    """Runs fn(job, *args) after the response. fn can set job["progress"]; result/error recorded."""
    job_id = str(uuid.uuid4())
    job = JOBS[job_id] = {"id": job_id, "status": "queued", "progress": 0, "result": None, "error": None}

    def run():
        job["status"] = "running"
        try:
            job["result"] = fn(job, *args)
            job["status"] = "done"
        except Exception as e:
            job["status"], job["error"] = "failed", str(e)

    background_tasks.add_task(run)
    return {"job_id": job_id, "status_url": f"/jobs/{job_id}"}


def get_job(job_id: str) -> dict:
    if job_id not in JOBS:
        raise HTTPException(404, "unknown job")
    return JOBS[job_id]
```

```python
from fastapi import BackgroundTasks

def import_rows(job, n):
    for i in range(n):
        ...                                         # do one unit of work
        job["progress"] = round((i + 1) / n * 100)
    return {"imported": n}

@app.post("/jobs", status_code=202)
def create(bg: BackgroundTasks):
    return start_job(bg, import_rows, 10_000)

@app.get("/jobs/{job_id}")
def status(job_id: str):
    return get_job(job_id)
```

**Moving to production:** `JOBS` lives in one process's memory, so it's lost on restart and not shared between workers. Keep the same two endpoints, but store job state in a database and run the work in a queue worker.

---

## 4. Optimistic locking: no more silent overwrites

### The problem

Alice and Bob both open document version 1. Alice saves. Bob saves a second later, and Alice's change disappears without anyone noticing. This is the **lost update** problem.

### Step 1: Version every record

Add a `version` integer column, and increment it on every write.

### Step 2: Write only if the version hasn't changed

Do the check *in the same statement* as the update. Checking first and writing second leaves a gap where another request can slip in.

### The complete function

```python
import sqlite3


def update_if_version(db_path: str, doc_id: str, expected_version: int, title: str) -> bool:
    """Compare-and-set in one statement. False -> someone changed it first (return 412)."""
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "UPDATE documents SET title = ?, version = version + 1 WHERE id = ? AND version = ?",
            (title, doc_id, expected_version))
        return cur.rowcount == 1
```

### Step 3: Expose it over HTTP with ETag and If-Match

HTTP has standard headers for this. `GET` returns the version as an `ETag`, and `PUT` must send it back in `If-Match`:

```python
from fastapi import Header, HTTPException, Response

@app.put("/documents/{doc_id}")
def update(doc_id: str, body: dict, response: Response, if_match: str = Header(None)):
    if if_match is None:
        raise HTTPException(428, "If-Match header required")
    version = int(if_match.strip('"'))                   # ETags are quoted: "3"
    if not update_if_version("app.db", doc_id, version, body["title"]):
        raise HTTPException(412, "document changed; re-fetch and retry")
    response.headers["ETag"] = f'"{version + 1}"'
    return {"ok": True}
```

- **428 Precondition Required:** the client didn't send `If-Match`. Without this, clients could skip the check just by leaving the header out.
- **412 Precondition Failed:** someone else changed the document first. The client should re-fetch and retry.

---

## Testing all four

```python
from fastapi import BackgroundTasks, FastAPI
from fastapi.testclient import TestClient

app = FastAPI()
log = add_request_id(app)
add_rate_limit(app, rate=0.001, burst=2)


@app.get("/x")
def x():
    return {}


@app.post("/jobs", status_code=202)
def create(bg: BackgroundTasks):
    return start_job(bg, lambda job, n: n * 2, 21)


def test_everything(tmp_path):
    c = TestClient(app)
    assert c.get("/x", headers={"X-Request-ID": "abc"}).headers["X-Request-ID"] == "abc"
    job = c.post("/jobs").json()
    assert JOBS[job["job_id"]]["result"] == 42           # TestClient runs background tasks
    r = c.get("/x")                                      # bucket of 2 is now empty
    assert r.status_code == 429 and "Retry-After" in r.headers
```

---

## Recap

- **Request IDs:** middleware + `ContextVar` + a logging filter, so every line is traceable.
- **Rate limits:** a token bucket per client, `time.monotonic()`, and `Retry-After`.
- **Background jobs:** return 202 plus a status URL, and always record the result or the error.
- **Optimistic locking:** `UPDATE ... WHERE version = ?` in one statement, exposed with `ETag`, `If-Match`, 428 and 412.

*Next: the backend logic patterns I write every week.*
