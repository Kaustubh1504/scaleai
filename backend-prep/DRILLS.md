# Drills: write these from memory

35 short templates. The goal is muscle memory: when a problem needs "a cursor
loop" or "retry with backoff", your hands write it while your head thinks
about the actual rule.

**How to drill**

1. Read one template and say out loud what each line is for.
2. Close this file. Write it in `drills/scratch.py` from memory.
3. Compare line by line. Fix only what you missed, then write it again.
4. Repeat until you can write it with no mistakes in one go, then tick a box.
   Aim for 10–15 clean reps per template **spread over days** (3 today, 3
   tomorrow, 3 in three days beats 10 in one sitting).

Tiers: **★ daily** (the core of almost every problem), **◆ every 2–3 days**,
**○ weekly**. Names, limits and status codes change per problem; the shape doesn't.

| # | Template | Tier | Reps |
|---|---|---|---|
| 1 | Safe GET | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 2 | POST + error mapping | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 3 | Page-number pagination | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 4 | Offset/limit pagination | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 5 | Cursor generator + loop guard | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 6 | Retry + backoff + jitter | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 7 | 429 + Retry-After | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 8 | Token bucket rate limiter | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 9 | Token auth + refresh on 401 | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 10 | TTL cache | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 11 | Safe nested get | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 12 | Count + tie-break + top-k | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 13 | Group by + aggregate | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 14 | Join by id + latest wins | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 15 | CSV with bad rows | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 16 | JSONL with bad lines | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 17 | Normalize values | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 18 | Flatten nested JSON | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 19 | Time windows | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 20 | Thread pool with failures | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 21 | asyncio + semaphore | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 22 | Worker queue (threads) | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 23 | FastAPI CRUD | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 24 | FastAPI CSV upload → JSON → save | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 25 | Background job API (202 + poll) | ○ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 26 | LLM call → validated JSON | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 27 | LLM over many rows (cache + concurrency) | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 28 | Load balancer | ○ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 29 | Priority scheduler (heapq) | ○ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 30 | pytest patterns | ★ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 31 | BFS crawl | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 32 | Checkpoint / resume | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 33 | SQLite store | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 34 | Idempotent POST (client + server) | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |
| 35 | Messy CSV: delimiter + header aliases | ◆ | ☐☐☐☐☐ ☐☐☐☐☐ |

Shared imports for the whole sheet (write these once at the top of `scratch.py`):

```python
from __future__ import annotations
import asyncio, csv, heapq, io, itertools, json, random, re, threading, queue
from collections import Counter, OrderedDict, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import httpx
```

---

## A. Calling an API

### 1. Safe GET ★

```python
class ApiError(Exception):
    def __init__(self, status, path, message=""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


def get_json(client, path, headers=None, params=None):
    try:
        resp = client.get(path, headers=headers, params=params, timeout=5)
    except httpx.TransportError as exc:
        raise ApiError(None, path, repr(exc)) from exc
    if resp.status_code == 404:
        return None
    if not resp.is_success:
        raise ApiError(resp.status_code, path, resp.text[:200])
    return resp.json()
```

Say: *timeout on every call; status before `.json()`; wrap with `from exc`.*

### 2. POST + error mapping ★

```python
class AuthError(ApiError): pass
class Conflict(ApiError): pass
class Invalid(ApiError): pass

ERRORS = {401: AuthError, 403: AuthError, 409: Conflict, 422: Invalid}


def create(client, token, body):
    path = "/v1/projects"
    resp = client.post(path, json=body, headers={"Authorization": f"Bearer {token}"}, timeout=5)
    if resp.status_code in (200, 201):
        return resp.json()
    raise ERRORS.get(resp.status_code, ApiError)(resp.status_code, path, resp.text[:200])
```

Say: *`json=` for a JSON body (`data=` is a form); one dict maps status → error.*

---

## B. Pagination

### 3. Page-number ★

```python
def fetch_pages(client, headers, per_page=20):
    out = []
    for page in itertools.count(1):
        body = get_json(client, "/v1/items", headers, {"page": page, "per_page": per_page})
        out += body["data"]
        if not body["data"] or page >= body["total_pages"]:
            return out
```

### 4. Offset/limit ◆

```python
def fetch_offset(client, headers, limit=50):
    out = []
    while True:
        body = get_json(client, "/v1/items", headers, {"offset": len(out), "limit": limit})
        out += body["items"]
        if len(body["items"]) < body.get("limit", limit):    # short or empty page = last
            return out
```

Say: *offset = what I've received so far; the server may cap my limit.*

### 5. Cursor generator + loop guard ★

```python
def iter_cursor(client, headers, params=None):
    params = dict(params or {})
    seen = set()
    while True:
        body = get_json(client, "/v1/events", headers, params)
        yield from body["results"]
        cursor = body.get("next_cursor")
        if not cursor:
            return
        if cursor in seen:
            raise RuntimeError(f"cursor {cursor!r} repeated")
        seen.add(cursor)
        params["cursor"] = cursor
```

Say: *`yield` makes it lazy; copy params so I don't change the caller's dict.*

---

## C. Reliability

### 6. Retry + backoff + jitter ★

```python
def with_retries(client, method, path, *, clock, rng, attempts=4, base=0.5, cap=8.0, **kw):
    for attempt in range(1, attempts + 1):
        try:
            resp = client.request(method, path, **kw)
        except httpx.TransportError:
            status = None
        else:
            if resp.is_success:
                return resp
            if resp.status_code not in (500, 502, 503, 504):
                raise ApiError(resp.status_code, path)
            status = resp.status_code
        if attempt < attempts:
            d = min(cap, base * 2 ** (attempt - 1))
            clock.sleep(rng.uniform(d / 2, d))
    raise ApiError(status, path, f"gave up after {attempts}")
```

Say: *retry 5xx and network errors, never 4xx; no sleep after the last try.*

### 7. 429 + Retry-After ◆

```python
def retry_after(resp, default=1.0):
    try:
        return max(0.0, float(resp.headers["Retry-After"]))
    except (KeyError, ValueError):
        return default


def get_respecting_429(client, path, *, clock, max_429=10):
    for _ in range(max_429):
        resp = client.get(path)
        if resp.status_code != 429:
            return resp
        clock.sleep(retry_after(resp))
    raise ApiError(429, path, "rate limited too long")
```

### 8. Token bucket rate limiter ◆

```python
class TokenBucket:
    def __init__(self, rate_per_s, burst, clock):
        self.rate, self.burst, self.clock = rate_per_s, burst, clock
        self.tokens = float(burst)
        self.updated = clock.time()

    def _refill(self):
        now = self.clock.time()
        self.tokens = min(self.burst, self.tokens + (now - self.updated) * self.rate)
        self.updated = now

    def acquire(self):                       # wait until a token is free
        self._refill()
        if self.tokens < 1:
            self.clock.sleep((1 - self.tokens) / self.rate)
            self._refill()
        self.tokens -= 1

    def try_acquire(self) -> bool:           # server side: allow or 429
        self._refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
```

Say: *refill by elapsed time × rate, cap at burst; `try_acquire` is the server-side limiter.*

### 9. Token auth + refresh on 401 ◆

```python
class AuthClient:
    def __init__(self, http, client_id, secret, clock):
        self.http, self.client_id, self.secret, self.clock = http, client_id, secret, clock
        self.token, self.expires_at = None, 0.0
        self.lock = threading.Lock()

    def _token(self, force=False):
        with self.lock:
            if force or self.token is None or self.clock.time() >= self.expires_at - 30:
                resp = self.http.post("/oauth/token", data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id, "client_secret": self.secret})
                resp.raise_for_status()
                body = resp.json()
                self.token = body["access_token"]
                self.expires_at = self.clock.time() + body["expires_in"]
            return self.token

    def get(self, path, **kw):
        for force in (False, True):                       # second try: fresh token after a 401
            headers = {"Authorization": f"Bearer {self._token(force)}"}
            resp = self.http.get(path, headers=headers, **kw)
            if resp.status_code != 401:
                break
        resp.raise_for_status()
        return resp
```

Say: *lazy token, refresh early, one retry on 401, lock so threads refresh once.*

### 10. TTL cache ◆

```python
class TTLCache:
    def __init__(self, ttl, clock, max_items=1000):
        self.ttl, self.clock, self.max_items = ttl, clock, max_items
        self.data = OrderedDict()                       # key -> (expires_at, value)

    def get(self, key, default=None):
        hit = self.data.get(key)
        if hit is None or self.clock.time() >= hit[0]:
            self.data.pop(key, None)
            return default
        self.data.move_to_end(key)                      # LRU: recently used
        return hit[1]

    def set(self, key, value):
        self.data[key] = (self.clock.time() + self.ttl, value)
        self.data.move_to_end(key)
        if len(self.data) > self.max_items:
            self.data.popitem(last=False)               # drop least recently used
```

---

## D. Data

### 11. Safe nested get ★

```python
def get_path(obj, path, default=None):
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return default
    return cur


def first(obj, paths, default=None):                  # first non-blank of several fields
    for p in paths:
        v = get_path(obj, p)
        if v not in (None, "", [], {}):
            return v
    return default
```

### 12. Count + tie-break + top-k ★

```python
counts = Counter(r["customer_id"] for r in rows)
best_id, best_n = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))    # ties -> smallest id
top3 = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]        # top-k, stable order
top3_big = heapq.nlargest(3, counts.items(), key=lambda kv: (kv[1], -kv[0]))
```

Say: *always state the tie rule; never rely on `most_common` for ties.*

### 13. Group by + aggregate ★

```python
groups = defaultdict(list)
for r in rows:
    groups[r["team"]].append(r["amount"])

summary = {team: {"count": len(a), "total": sum(a), "avg": round(sum(a) / len(a), 2), "max": max(a)}
           for team, a in groups.items()}
report = sorted(summary.items(), key=lambda kv: (-kv[1]["total"], kv[0]))
```

### 14. Join by id + latest wins ★

```python
users_by_id = {u["id"]: u for u in users}                    # index once: O(n + m)
joined = [{**o, "user": users_by_id.get(o["user_id"])} for o in orders]
orphans = [o for o in orders if o["user_id"] not in users_by_id]

latest = {}
for r in records:                                            # later wins on equal time
    cur = latest.get(r["id"])
    if cur is None or r["updated_at"] >= cur["updated_at"]:
        latest[r["id"]] = r
current = [r for r in latest.values() if not r.get("deleted")]
```

### 15. CSV with bad rows ★

```python
def read_csv(text):
    rows, errors = [], []
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    reader.fieldnames = [h.strip().lower() for h in reader.fieldnames or []]
    for row in reader:
        line = reader.line_num
        if None in row or None in row.values():
            errors.append({"line": line, "error": "wrong number of columns"})
            continue
        row = {k: v.strip() for k, v in row.items()}
        if not any(row.values()):
            continue
        rows.append(row)
    return rows, errors
```

Say: *`csv` module, never `split(",")`; `line_num` for the real line.*

### 16. JSONL with bad lines ★

```python
def read_jsonl(text):
    records, errors = [], []
    for n, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append({"line": n, "error": exc.msg})
            continue
        if not isinstance(obj, dict):
            errors.append({"line": n, "error": "not an object"})
            continue
        records.append(obj)
    return records, errors
```

### 17. Normalize values ★

```python
TRUE, FALSE = {"true", "yes", "y", "1"}, {"false", "no", "n", "0"}


def to_bool(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return True if s in TRUE else False if s in FALSE else None


def to_int(v):
    if isinstance(v, bool):                 # bool is a subclass of int
        return None
    try:
        return int(str(v).strip())
    except ValueError:
        return None


def to_money(v):
    try:
        return Decimal(str(v).replace("$", "").replace(",", "").strip()).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def to_utc(s):
    dt = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def from_epoch(n):
    n = float(n)
    if n >= 1e11:                           # too big for seconds: it's milliseconds
        n /= 1000
    return datetime.fromtimestamp(n, timezone.utc)


def clean_email(s):
    s = s.strip().lower()
    return s if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", s) else None
```

### 18. Flatten nested JSON ◆

```python
def flatten(obj, sep="."):
    out = {}

    def walk(v, prefix):
        if isinstance(v, dict):
            for k, child in v.items():
                walk(child, f"{prefix}{sep}{k}" if prefix else k)
        elif isinstance(v, list):
            for i, child in enumerate(v):
                walk(child, f"{prefix}{sep}{i}")
        else:
            out[prefix] = v

    walk(obj, "")
    return out


def to_csv_text(records):
    flats = [flatten(r) for r in records]
    columns = list(dict.fromkeys(k for f in flats for k in f))   # union, first-seen order
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")                  # csv writes None as ""
    w.writerow(columns)
    w.writerows([f.get(c) for c in columns] for f in flats)
    return buf.getvalue()
```

### 19. Time windows ◆

```python
def bucket(ts: datetime, minutes=60):                   # start of its fixed window
    size = minutes * 60
    secs = int(ts.timestamp())
    return datetime.fromtimestamp(secs - secs % size, timezone.utc)

per_hour = Counter(bucket(to_utc(e["at"])) for e in events)
per_day = Counter(to_utc(e["at"]).date() for e in events)

in_range = [e for e in events if start <= to_utc(e["at"]) < end]   # half-open [start, end)


class SlidingWindow:                                    # "how many in the last N seconds"
    def __init__(self, seconds, clock):
        self.seconds, self.clock, self.times = seconds, clock, deque()

    def add(self):
        self.times.append(self.clock.time())

    def count(self):
        cutoff = self.clock.time() - self.seconds
        while self.times and self.times[0] <= cutoff:
            self.times.popleft()
        return len(self.times)
```

Say: *windows are half-open; convert to UTC before bucketing.*

---

## E. Concurrency

### 20. Thread pool with failures ◆

```python
def fetch_many(ids, fetch_one, workers=8):
    results, errors = [], {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fetch_one, i) for i in ids]
    for i, fut in zip(ids, futures):              # input order; failures don't stop the rest
        try:
            results.append(fut.result())
        except Exception as exc:
            errors[i] = repr(exc)
    return results, errors
```

### 21. asyncio + semaphore ◆

```python
async def fetch_all(client: httpx.AsyncClient, paths, limit=5):
    sem = asyncio.Semaphore(limit)

    async def one(path):
        async with sem:
            resp = await client.get(path)
            resp.raise_for_status()
            return resp.json()

    return await asyncio.gather(*(one(p) for p in paths), return_exceptions=True)

# run: asyncio.run(fetch_all(client, paths))
```

### 22. Worker queue (threads) ◆

```python
class WorkerPool:
    def __init__(self, handle, workers=2):
        self.handle = handle
        self.q = queue.Queue()
        self.status = {}                                  # job_id -> dict
        self.lock = threading.Lock()
        self.threads = [threading.Thread(target=self._run, daemon=True) for _ in range(workers)]
        for t in self.threads:
            t.start()

    def submit(self, job_id, payload):
        with self.lock:
            self.status[job_id] = {"state": "queued", "result": None, "error": None}
        self.q.put((job_id, payload))

    def _run(self):
        while (item := self.q.get()) is not None:
            job_id, payload = item
            self._set(job_id, state="running")
            try:
                self._set(job_id, state="done", result=self.handle(payload))
            except Exception as exc:                      # one bad job must not kill the worker
                self._set(job_id, state="failed", error=str(exc) or type(exc).__name__)

    def _set(self, job_id, **fields):
        with self.lock:
            self.status[job_id].update(fields)

    def shutdown(self):
        for _ in self.threads:
            self.q.put(None)                              # one stop signal per worker
        for t in self.threads:
            t.join()
```

---

## F. Building a service

### 23. FastAPI CRUD ★

```python
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    priority: int = Field(3, ge=1, le=5)


class ItemPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    priority: int | None = Field(None, ge=1, le=5)


class Item(ItemIn):
    id: int


def create_app():
    app = FastAPI()
    items: dict[int, Item] = {}
    ids = itertools.count(1)

    def get_or_404(item_id):
        if item_id not in items:
            raise HTTPException(404, f"item {item_id} not found")
        return items[item_id]

    @app.post("/items", status_code=201, response_model=Item)
    def create(body: ItemIn):
        if any(i.name.lower() == body.name.lower() for i in items.values()):
            raise HTTPException(409, "name taken")
        item = Item(id=next(ids), **body.model_dump())
        items[item.id] = item
        return item

    @app.get("/items")
    def list_items(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
        ordered = [items[k] for k in sorted(items)]
        return {"items": ordered[offset:offset + limit], "total": len(ordered)}

    @app.get("/items/{item_id}", response_model=Item)
    def read(item_id: int):
        return get_or_404(item_id)

    @app.patch("/items/{item_id}", response_model=Item)
    def update(item_id: int, body: ItemPatch):
        item = get_or_404(item_id).model_copy(update=body.model_dump(exclude_unset=True))
        items[item_id] = item
        return item

    @app.delete("/items/{item_id}", status_code=204)
    def delete(item_id: int):
        get_or_404(item_id)
        del items[item_id]

    return app
```

Say: *201 create, 204 delete, 404 unknown, 409 duplicate, 422 is automatic.*

### 24. FastAPI CSV upload → JSON → save ★

```python
from fastapi import FastAPI, File, HTTPException, UploadFile


def save_json(path: Path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)                                     # atomic: never a half-written file


def create_upload_app(storage: Path):
    app = FastAPI()
    storage.mkdir(parents=True, exist_ok=True)

    @app.post("/upload", status_code=201)
    async def upload(file: UploadFile = File(...)):
        raw = await file.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(400, "file must be UTF-8 CSV")
        rows, errors = read_csv(text)                     # template 15
        upload_id = f"up_{len(list(storage.glob('*.json'))) + 1}"
        save_json(storage / f"{upload_id}.json", rows)
        return {"id": upload_id, "accepted": len(rows), "rejected": errors}

    @app.get("/uploads/{upload_id}")
    def get_upload(upload_id: str):
        path = storage / f"{upload_id}.json"
        if not re.fullmatch(r"up_\d+", upload_id) or not path.exists():
            raise HTTPException(404, "unknown upload")
        return json.loads(path.read_text())

    return app

# test: client.post("/upload", files={"file": ("a.csv", b"name,age\nAnn,3\n", "text/csv")})
```

### 25. Background job API (202 + poll) ○

```python
import uuid
from contextlib import asynccontextmanager


def create_job_app(handle):
    pool = {}

    @asynccontextmanager
    async def lifespan(app):
        pool["p"] = WorkerPool(handle)                    # template 22
        yield
        pool["p"].shutdown()

    app = FastAPI(lifespan=lifespan)

    @app.post("/jobs", status_code=202)
    def submit(payload: dict):
        job_id = uuid.uuid4().hex
        pool["p"].submit(job_id, payload)
        return {"job_id": job_id, "state": "queued"}

    @app.get("/jobs/{job_id}")
    def status(job_id: str):
        job = pool["p"].status.get(job_id)
        if job is None:
            raise HTTPException(404, "unknown job")
        return {"job_id": job_id, **job}

    return app

# test: with TestClient(create_job_app(fn)) as c:   (the `with` runs lifespan)
```

---

## G. LLM

### 26. LLM call → validated JSON ★

```python
CATEGORIES = {"billing", "bug", "feature_request", "other"}

PROMPT = """Classify the support ticket into exactly one category.
Allowed categories: billing, bug, feature_request, other.
Reply with JSON only, no prose, in this shape:
{{"category": "<one of the allowed>", "confidence": <number 0-1>}}

Ticket:
{text}"""


def parse_llm_json(text):
    start, end = text.find("{"), text.rfind("}")           # outermost {...}: skips fences and prose
    if start == -1 or end == -1:
        raise ValueError("no JSON object in reply")
    return json.loads(text[start:end + 1])


def classify(text, call_llm, attempts=3):
    """call_llm(prompt) -> str. Validate; retry bad output; fall back to 'other'."""
    for _ in range(attempts):
        try:
            data = parse_llm_json(call_llm(PROMPT.format(text=text)))
            category = str(data["category"]).strip().lower()
            if category in CATEGORIES:
                return {"category": category, "confidence": float(data.get("confidence", 0))}
        except (ValueError, KeyError, TypeError):
            pass
    return {"category": "other", "confidence": 0.0, "fallback": True}
```

The real call, OpenAI SDK (`pip install openai`; model name comes from the interviewer):

```python
from openai import OpenAI

llm = OpenAI(api_key=API_KEY)             # or reads OPENAI_API_KEY from the environment


def call_llm(prompt: str) -> str:
    resp = llm.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": "You reply with JSON only."},
                  {"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},   # JSON mode, if the model supports it
        timeout=30,
    )
    return resp.choices[0].message.content
```

Say: *fix the allowed labels in the prompt, demand JSON, then validate in code anyway; never trust the model's output.*

### 27. LLM over many rows (cache + concurrency) ◆

```python
def classify_rows(rows, call_llm, workers=4):
    unique = {}                                      # same text -> one LLM call
    for r in rows:
        unique.setdefault(r["text"].strip().lower(), r["text"])
    with ThreadPoolExecutor(max_workers=workers) as pool:   # cap concurrent LLM calls
        labels = dict(zip(unique, pool.map(lambda t: classify(t, call_llm), unique.values())))
    return [{**r, **labels[r["text"].strip().lower()]} for r in rows]
```

Scale-up answer: *batch rows, cap concurrency (pool size or token bucket), cache
repeats, retry 429/5xx with backoff, and for big files a queue + workers that
write results as they go so a crash can resume.*

---

## H. Small systems

### 28. Load balancer ○

```python
class LoadBalancer:
    def __init__(self, backends):
        self.backends = list(backends)
        self.healthy = set(self.backends)
        self.active = Counter()                         # in-flight requests per backend
        self.rr = 0
        self.lock = threading.Lock()

    def mark(self, backend, healthy: bool):             # from heartbeats / failed calls
        with self.lock:
            (self.healthy.add if healthy else self.healthy.discard)(backend)

    def _alive(self):
        alive = [b for b in self.backends if b in self.healthy]
        if not alive:
            raise RuntimeError("no healthy backends")
        return alive

    def pick_round_robin(self):
        with self.lock:
            alive = self._alive()
            b = alive[self.rr % len(alive)]
            self.rr += 1
            return b

    def pick_least_busy(self):
        with self.lock:
            b = min(self._alive(), key=lambda x: (self.active[x], self.backends.index(x)))
            self.active[b] += 1
            return b

    def done(self, backend):
        with self.lock:
            self.active[backend] -= 1
```

### 29. Priority scheduler (heapq) ○

```python
class Scheduler:
    def __init__(self):
        self.heap = []
        self.seq = 0                                    # tie-break: first in, first out

    def push(self, task, priority, run_at=0.0):
        heapq.heappush(self.heap, (run_at, -priority, self.seq, task))   # earliest, then highest
        self.seq += 1

    def pop_ready(self, now):
        if self.heap and self.heap[0][0] <= now:
            return heapq.heappop(self.heap)[-1]
        return None
```

Say: *heap of tuples; a sequence number breaks ties so tasks are never compared.*

---

## I. Tests

### 30. pytest patterns ★

```python
import pytest


def test_happy_path():
    assert to_bool(" Yes ") is True


@pytest.mark.parametrize("raw, want", [("1", 1), (" 7 ", 7), ("x", None), (True, None)])
def test_to_int(raw, want):
    assert to_int(raw) == want


def test_raises():
    with pytest.raises(ValueError):
        parse_llm_json("no json here")


def test_cursor_with_fake_server():
    pages = {None: {"results": [1, 2], "next_cursor": "b"},
             "b": {"results": [3], "next_cursor": None}}

    def handler(request):
        return httpx.Response(200, json=pages[request.url.params.get("cursor")])

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://t")
    assert list(iter_cursor(client, {})) == [1, 2, 3]


def test_classify_retries_then_falls_back():
    fence = "`" * 3
    good = f'{fence}json\n{{"category": "Bug"}}\n{fence}'
    replies = iter(["not json", '{"category": "nonsense"}', good])
    assert classify("app crashes", lambda p: next(replies))["category"] == "bug"
    assert classify("?", lambda p: "garbage")["fallback"] is True
```

Say: *expected values from the statement; a fake server, never the network.*

---

## J. Mock-round extras

### 31. BFS crawl ◆

```python
def crawl(root_id, fetch, max_depth=None):
    """fetch(id) -> node dict, or None for 404. Returns (visited in BFS order, missing ids)."""
    seen = {root_id}
    q = deque([(root_id, 0)])
    visited, missing = [], []
    while q:
        node_id, depth = q.popleft()
        node = fetch(node_id)
        if node is None:
            missing.append(node_id)
            continue
        visited.append(node_id)
        if max_depth is not None and depth >= max_depth:
            continue
        for child in node.get("children", []):
            if child not in seen:                 # mark when queued: each node fetched once
                seen.add(child)
                q.append((child, depth + 1))
    return visited, sorted(missing)
```

Say: *BFS = `deque` + `popleft`; mark seen when queuing, not when visiting.*

### 32. Checkpoint / resume ◆

```python
def process_all(items, handle, checkpoint: Path):
    fresh = {"done": {}, "failed": {}}
    state = json.loads(checkpoint.read_text()) if checkpoint.exists() else fresh
    for item in items:
        key = str(item["id"])                     # JSON keys are always strings
        if key in state["done"]:
            continue                              # finished before the crash
        try:
            state["done"][key] = handle(item)
            state["failed"].pop(key, None)
        except Exception as exc:
            state["failed"][key] = repr(exc)      # not done: retried on the next run
        save_json(checkpoint, state)              # template 24: atomic write after every item
    return state
```

Say: *save after each unit of work, atomically; skip what's done; failures stay retryable.*

### 33. SQLite store ◆

```python
import sqlite3


class Store:
    def __init__(self, path):
        self.path = str(path)
        self.lock = threading.Lock()              # one writer at a time: no "database is locked"
        self.run("""CREATE TABLE IF NOT EXISTS rows (
                        id TEXT PRIMARY KEY, job_id TEXT, text TEXT,
                        status TEXT NOT NULL DEFAULT 'pending', label TEXT)""")

    def run(self, sql, params=(), many=False):
        with self.lock:
            con = sqlite3.connect(self.path, timeout=10)
            try:
                with con:                         # commits, or rolls back on error
                    cur = con.executemany(sql, params) if many else con.execute(sql, params)
                    return cur.fetchall()
            finally:
                con.close()

    def add(self, job_id, rows):
        self.run("INSERT OR IGNORE INTO rows (id, job_id, text) VALUES (?, ?, ?)",
                 [(r["id"], job_id, r["text"]) for r in rows], many=True)

    def pending(self):
        return self.run("SELECT id, text FROM rows WHERE status = 'pending' ORDER BY id")

    def finish(self, row_id, label):
        self.run("UPDATE rows SET status = 'done', label = ? WHERE id = ?", (label, row_id))

    def progress(self, job_id):
        return dict(self.run("SELECT status, COUNT(*) FROM rows WHERE job_id = ? GROUP BY status",
                             (job_id,)))
```

Say: *`?` placeholders, never f-strings in SQL; a status column makes resume = "process pending".*

### 34. Idempotent POST (client and server) ◆

```python
def pay(client, order_id, amount_cents, *, clock, rng):
    key = f"pay:{order_id}"                       # derived from the data, never uuid4()
    return with_retries(client, "POST", "/v1/payments", clock=clock, rng=rng,       # template 6
                        json={"order_id": order_id, "amount_cents": amount_cents},
                        headers={"Idempotency-Key": key})


class IdempotencyStore:                           # server side
    def __init__(self):
        self.seen = {}                            # key -> (body fingerprint, result)
        self.lock = threading.Lock()

    def run(self, key, body, create):
        fp = json.dumps(body, sort_keys=True)
        with self.lock:
            if key in self.seen:
                old_fp, result = self.seen[key]
                if old_fp != fp:
                    raise Conflict(409, key, "key reused with a different body")    # template 2
                return result, False              # replay: same answer, no second payment
            result = create(body)
            self.seen[key] = (fp, result)
            return result, True
```

Say: *same key and same body on every retry; the server replays the first result.*

### 35. Messy CSV: delimiter + header aliases ◆

```python
ALIASES = {"email_address": "email", "e_mail": "email", "full_name": "name",
           "customer_name": "name", "organisation": "company", "org": "company"}


def norm_header(h):
    return re.sub(r"[^a-z0-9]+", "_", h.strip().lower()).strip("_")


def read_messy_csv(raw: bytes):
    text = raw.decode("utf-8-sig")                               # drops a BOM
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    delim = max(",;\t", key=first.count)                         # ties / zero -> ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delim)
    header, rows, errors = None, [], []
    for rec in reader:
        if not any(c.strip() for c in rec):
            continue
        if header is None:
            header = [ALIASES.get(norm_header(h), norm_header(h)) for h in rec]
            continue
        if any(c.strip() for c in rec[len(header):]):
            errors.append({"line": reader.line_num, "error": "too many fields"})
            continue
        rec = rec + [""] * (len(header) - len(rec))              # pad short rows
        rows.append({h: v.strip() for h, v in zip(header, rec)})
    return rows, errors
```

Say: *decode with `utf-8-sig`, normalize every header, then map aliases to one name.*
