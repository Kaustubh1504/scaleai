# Backend templates

Patterns that come up again and again in the problems. Learn the shape, then
adapt names, limits and status codes to what each statement says.

Conventions used throughout: `client` is an `httpx.Client` with the base URL
set, `clock` has `.time()` / `.sleep(s)` (inject it, never call `time.sleep`),
`rng` is a `random.Random`.

---

## 0. Mental model: before you write a line

**Every API task is the same four questions.** Answer them out loud, in this
order, before you code:

1. **How do I get in?** Auth: where the key or token goes (header, query, body),
   what it's called, whether it expires.
2. **How do I get everything?** Pagination: page / offset / cursor / `Link`,
   the max page size, and *how it tells you it's done*.
3. **What can go wrong?** Which statuses happen, which are worth retrying,
   rate limits, timeouts, malformed bodies.
4. **What shape is the data?** Where the list lives (`results`, `data`,
   `items`), which fields can be missing / null / the wrong type.

### Rules for consuming an API

**Explore first (the first ~10 minutes)**

* Read the spec or statement, then **hit each endpoint once and print the raw
  response** (`print(resp.status_code, resp.headers, resp.text[:500])`). Never
  write parsing code for a response you haven't seen.
* Write down the 4 answers above as a comment at the top of your file. That is
  also your plan to say to the interviewer.
* Ignore what you don't need: deprecated / legacy endpoints, write endpoints in
  a read-only task.

**Every request**

* Has a **timeout**. The default can be long or infinite.
* Sends **auth** exactly as specified, built in one place (`headers = {...}`) and
  reused, never rebuilt in every call.
* Has its **status checked before `.json()`**. A 500 HTML page is not your data.
* Uses `params={...}` for the query string, never string-formatted URLs
  (encoding, injection). Validate any id you put in a path.

**Getting everything**

* Loop until the API says stop (`next` null, short page, `has_more` false), not
  until "it looks done". Use the **max page size** the spec allows.
* Filter **on the server** when a parameter exists (`?status=open`). It means
  fewer pages and fewer requests.
* Guard against infinite loops (repeated cursor, page count cap).
* **No request per item** (N+1). Fetch lists, build a `dict` by id, join in memory.

**Failures: decide per class, never one blanket `except`**

| what happened | default action |
|---|---|
| 2xx | parse it, and still check the body is the shape you expect |
| 400 / 422 | your bug: raise, don't retry |
| 401 | token expired: refresh once, retry once, then raise |
| 403 / 404 | raise (or `None` for 404 if the statement says "missing") |
| 409 | conflict: raise; re-read the state before trying again |
| 429 | wait `Retry-After`, retry, but cap how many in a row |
| 5xx / timeout / connection error | retry with backoff + jitter, a bounded number of times |
| POST / PATCH failing with 5xx | retry **only** with an idempotency key, or you may do it twice |

* Raise **your own exception** carrying `status` and `path`, chained with
  `raise ... from exc`. Never swallow an error and return `[]`. "No data" and
  "failed" must look different.
* Don't sleep after the last attempt. Inject the clock so tests don't really wait.

**Data**

* Trust nothing: use `.get()` for optional fields, check types (`"12"` vs `12`,
  `"true"` vs `True`), handle `null`, empty strings, duplicates.
* Decide and state the rules: ties (smallest id wins), ordering (sort
  explicitly; dict / API order isn't a contract), timezones (convert to UTC),
  money (`Decimal`, never `float`).
* Keep bad records **out of the result but visible** (an `errors` list with the
  reason and the line or id), unless told to fail fast.

**Structure (what the interviewer grades)**

* Small functions: `fetch_*` (HTTP) → `iter_*` (pagination) → pure logic
  (count / join / pick) → result. The pure part is testable without HTTP.
* Constants for magic numbers (`PAGE_SIZE = 50`, `TIMEOUT_S = 5`).
* Generators (`yield`) for pagination, so the caller decides whether to stream or `list()`.
* Say the tradeoff when you make a choice ("one pass over open tickets
  instead of one request per customer: ~N/50 requests instead of N").

### Rules for building an API (FastAPI tasks)

* **Validate at the edge**: Pydantic models with constraints (`min_length`,
  `ge` / `le`); bad input gets 422 automatically. Don't re-validate by hand.
* **Status codes mean something**: `201` create, `204` delete (no body), `404`
  unknown id, `409` duplicate / conflict, `422` invalid. One consistent error
  body (`{"detail": ...}`).
* **Separate models** for create / patch / response; PATCH applies only
  `model_dump(exclude_unset=True)`.
* **Lists are paginated and ordered** (`limit` with a max, `offset`, `total`),
  sorted by a stable key.
* **State lives in the app factory** (`create_app()`), so every test gets a
  fresh app. Persist with write-to-temp then `replace()` (atomic).
* **Slow work doesn't block the request**: return `202` with a job id, poll
  `GET /jobs/{id}`.
* Make retried creates safe: accept an `Idempotency-Key` and return the
  original result for a repeat.

### The 30-second self-review before you say "done"

- [ ] Ran it end to end in `__main__` and looked at the output
- [ ] Every request has a timeout, auth and a status check
- [ ] Reads **all** pages; tested with an empty result and a single page
- [ ] Each failure class does the right thing (try one 4xx, one 5xx, one timeout)
- [ ] Ties, ordering and empty input match the statement
- [ ] No request per item; request count is what you'd expect
- [ ] Names and structure an interviewer can read in one pass

---

## 1. One safe request

```python
import httpx

TIMEOUT_S = 5


class ApiError(Exception):
    def __init__(self, status: int | None, path: str, message: str = ""):
        super().__init__(f"{status if status is not None else 'no response'} on {path}: {message}")
        self.status = status
        self.path = path


def get_json(client: httpx.Client, path: str, *, headers: dict | None = None,
             params: dict | None = None):
    try:
        resp = client.get(path, headers=headers, params=params, timeout=TIMEOUT_S)
    except httpx.TransportError as exc:            # timeout, connection refused...
        raise ApiError(None, path, f"{type(exc).__name__}: {exc}") from exc
    if resp.status_code == 404:
        return None                                # only if the statement says 404 = "missing"
    if not resp.is_success:
        raise ApiError(resp.status_code, path, resp.text[:200])
    return resp.json()
```

If the statement just says "raise on non-2xx": `resp.raise_for_status()`.

Auth, depending on the spec:

```python
headers = {"Authorization": f"Bearer {token}"}     # bearer token
headers = {"X-Api-Key": api_key}                   # api key in a header
params = {"api_key": api_key}                      # api key in the query string
```

---

## 2. Pagination

### Page number (`?page=1&per_page=25`)

```python
def iter_pages(client, path, headers, per_page=25):
    page = 1
    while True:
        resp = client.get(path, headers=headers, params={"page": page, "per_page": per_page})
        resp.raise_for_status()
        items = resp.json()["results"]
        yield from items
        if len(items) < per_page:      # or: page >= body["total_pages"] / body["next"] is None
            break
        page += 1
```

### Offset / limit (`?offset=0&limit=50`)

```python
def iter_offset(client, path, headers, limit=50):
    offset = 0
    while True:
        resp = client.get(path, headers=headers, params={"offset": offset, "limit": limit})
        resp.raise_for_status()
        items = resp.json()["items"]
        yield from items
        if len(items) < limit:         # or: offset + len(items) >= body["total"]
            break
        offset += len(items)           # advance by what you got, not by limit
```

### Cursor (`?cursor=...`), with a loop guard

```python
def iter_cursor(client, path, headers, params=None):
    params = dict(params or {})
    seen: set[str] = set()
    while True:
        resp = client.get(path, headers=headers, params=params)
        resp.raise_for_status()
        body = resp.json()
        yield from body["results"]
        cursor = body.get("next_cursor")
        if not cursor:
            break
        if cursor in seen:             # server bug: same cursor again -> stop, don't spin forever
            raise RuntimeError(f"pagination loop: cursor {cursor!r} repeated")
        seen.add(cursor)
        params["cursor"] = cursor
```

---

## 3. Retries with exponential backoff + jitter

```python
TRANSIENT = frozenset({500, 502, 503, 504})


def backoff_delay(attempt: int, base_s: float, cap_s: float, rng) -> float:
    d = min(cap_s, base_s * 2 ** (attempt - 1))   # 0.5, 1, 2, 4, 8, 8...
    return rng.uniform(d / 2, d)                   # jitter: clients don't retry in lockstep


def request_with_retries(client, method, path, *, clock, rng,
                         max_attempts=4, base_s=0.5, cap_s=8.0, **kwargs) -> httpx.Response:
    status, reason = None, ""
    for attempt in range(1, max_attempts + 1):
        try:
            resp = client.request(method, path, **kwargs)
        except httpx.TransportError as exc:
            status, reason = None, repr(exc)                  # no response: retry
        else:
            if resp.is_success:
                return resp
            if resp.status_code not in TRANSIENT:
                raise ApiError(resp.status_code, path, resp.text[:200])   # 4xx: never retry
            status, reason = resp.status_code, resp.text[:200]
        if attempt < max_attempts:                            # no sleep after the last try
            clock.sleep(backoff_delay(attempt, base_s, cap_s, rng))
    raise ApiError(status, path, f"gave up after {max_attempts} attempts: {reason}")
```

Only retry non-idempotent requests (POST/PATCH) if they carry an idempotency
key: `headers={"Idempotency-Key": key}`, with the **same** key on every attempt.

### 429 with `Retry-After`

```python
def retry_after_s(resp: httpx.Response, default: float = 1.0) -> float:
    value = resp.headers.get("Retry-After")
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):    # missing, or an HTTP date: fall back
        return default

# inside the loop, before the TRANSIENT check:
#     if resp.status_code == 429:
#         clock.sleep(retry_after_s(resp)); continue    # cap how many 429s in a row you accept
```

---

## 4. Token auth with refresh on 401

```python
import threading


class TokenClient:
    def __init__(self, http: httpx.Client, client_id: str, client_secret: str, *, clock):
        self.http = http
        self.client_id = client_id
        self.client_secret = client_secret
        self.clock = clock
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = threading.Lock()           # two threads must not both refresh

    def _refresh(self) -> None:
        resp = self.http.post("/oauth/token", json={"client_id": self.client_id,
                                                    "client_secret": self.client_secret})
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._expires_at = self.clock.time() + body["expires_in"] - 30   # refresh a bit early

    def _get_token(self) -> str:
        with self._lock:
            if self._token is None or self.clock.time() >= self._expires_at:
                self._refresh()
            return self._token

    def get(self, path: str, **kwargs) -> httpx.Response:
        resp = self.http.get(path, headers={"Authorization": f"Bearer {self._get_token()}"}, **kwargs)
        if resp.status_code == 401:             # revoked early: refresh once and retry once
            with self._lock:
                self._token = None
            resp = self.http.get(path, headers={"Authorization": f"Bearer {self._get_token()}"}, **kwargs)
        resp.raise_for_status()
        return resp
```

---

## 5. TTL cache

```python
class TTLCache:
    def __init__(self, ttl_s: float, clock, max_items: int = 1000):
        self.ttl_s = ttl_s
        self.clock = clock
        self.max_items = max_items
        self._data: dict[str, tuple[float, object]] = {}   # key -> (expires_at, value)

    def get(self, key: str):
        hit = self._data.get(key)
        if hit is None:
            return None
        expires_at, value = hit
        if self.clock.time() >= expires_at:
            del self._data[key]
            return None
        return value

    def set(self, key: str, value) -> None:
        if len(self._data) >= self.max_items and key not in self._data:
            self._data.pop(next(iter(self._data)))          # evict the oldest insert
        self._data[key] = (self.clock.time() + self.ttl_s, value)
```

Only cache successes. For an LRU instead, use `collections.OrderedDict` with
`move_to_end(key)` on read and `popitem(last=False)` to evict.

---

## 6. Concurrency

### Threads (blocking I/O, keep input order, collect failures)

```python
from concurrent.futures import ThreadPoolExecutor, as_completed


def enrich_all(ids: list[str], fetch_one, max_workers: int = 8):
    results: dict[str, dict] = {}
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_one, i): i for i in ids}
        for fut in as_completed(futures):
            i = futures[fut]
            try:
                results[i] = fut.result()
            except Exception as exc:           # one bad item must not kill the batch
                errors[i] = f"{type(exc).__name__}: {exc}"
    return [results[i] for i in ids if i in results], errors   # back in input order
```

`pool.map(fetch_one, ids)` is shorter and keeps order, but the first exception
stops you from seeing the rest.

### asyncio with a concurrency limit

```python
import asyncio


async def fetch_all(client: httpx.AsyncClient, paths: list[str], limit: int = 5):
    sem = asyncio.Semaphore(limit)             # at most `limit` requests in flight

    async def one(path: str):
        async with sem:
            resp = await client.get(path)
            resp.raise_for_status()
            return resp.json()

    return await asyncio.gather(*(one(p) for p in paths), return_exceptions=True)
    # results are in input order; failures come back as exception objects
```

---

## 7. Messy data

### CSV with junk rows

```python
import csv
import io


def read_rows(text: str) -> tuple[list[dict], list[dict]]:
    good, bad = [], []
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))       # strip a BOM
    reader.fieldnames = [h.strip().lower() for h in reader.fieldnames or []]
    for row in reader:                     # DictReader skips fully blank lines itself
        line_no = reader.line_num          # real file line (enumerate drifts after a blank line)
        if None in row or any(v is None for v in row.values()):       # too many / too few cells
            bad.append({"line": line_no, "error": "wrong number of columns"})
            continue
        row = {k: v.strip() for k, v in row.items()}
        if not any(row.values()):
            continue                                                  # a row of empty cells: ",,"
        good.append(row)
    return good, bad
```

### JSONL with bad lines

```python
import json


def read_jsonl(text: str):
    records, errors = [], []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append({"line": line_no, "error": exc.msg})
            continue
        if not isinstance(obj, dict):
            errors.append({"line": line_no, "error": "not an object"})
            continue
        records.append(obj)
    return records, errors
```

### Normalising values

```python
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

TRUE, FALSE = {"true", "yes", "y", "1"}, {"false", "no", "n", "0"}


def to_bool(v) -> bool | None:
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return True if s in TRUE else False if s in FALSE else None


def to_money(v) -> Decimal | None:                  # never float for money
    try:
        return Decimal(str(v).replace("$", "").replace(",", "").strip()).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def to_utc(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
```

### Group, aggregate, join, latest-wins

```python
from collections import Counter, defaultdict

# count per key
counts = Counter(r["customer_id"] for r in rows)

# group then aggregate
by_team: defaultdict[str, list[dict]] = defaultdict(list)
for r in rows:
    by_team[r["team"]].append(r)
summary = {team: {"n": len(rs), "total": sum(r["amount"] for r in rs)} for team, rs in by_team.items()}

# winner: highest value, ties -> smallest id
best_id, best_n = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))

# deterministic output order
report = sorted(summary.items(), key=lambda kv: (-kv[1]["total"], kv[0]))

# join: index one side by id, then look up (O(n + m), not O(n * m))
users_by_id = {u["id"]: u for u in users}
joined = [{**o, "user_name": users_by_id.get(o["user_id"], {}).get("name")} for o in orders]

# latest record wins per id (tie on timestamp -> later in input wins)
latest: dict[str, dict] = {}
for r in rows:
    cur = latest.get(r["id"])
    if cur is None or r["updated_at"] >= cur["updated_at"]:
        latest[r["id"]] = r
```

---

## 8. FastAPI CRUD

```python
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    priority: int = Field(3, ge=1, le=5)


class ItemPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    priority: Optional[int] = Field(None, ge=1, le=5)


class Item(ItemCreate):
    id: int


def create_app() -> FastAPI:
    app = FastAPI()
    items: dict[int, Item] = {}        # state lives inside create_app: each app starts empty
    next_id = 1

    def get_or_404(item_id: int) -> Item:
        item = items.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"item {item_id} not found")
        return item

    @app.post("/items", status_code=201, response_model=Item)
    def create_item(body: ItemCreate) -> Item:
        nonlocal next_id
        if any(i.name.casefold() == body.name.casefold() for i in items.values()):
            raise HTTPException(status_code=409, detail="name already taken")
        item = Item(id=next_id, **body.model_dump())
        items[item.id] = item
        next_id += 1
        return item

    @app.get("/items")
    def list_items(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
        ordered = [items[k] for k in sorted(items)]
        return {"items": ordered[offset:offset + limit], "total": len(ordered)}

    @app.get("/items/{item_id}", response_model=Item)
    def get_item(item_id: int) -> Item:
        return get_or_404(item_id)

    @app.patch("/items/{item_id}", response_model=Item)
    def update_item(item_id: int, body: ItemPatch) -> Item:
        item = get_or_404(item_id)
        updated = item.model_copy(update=body.model_dump(exclude_unset=True))   # only sent fields
        items[item_id] = updated
        return updated

    @app.delete("/items/{item_id}", status_code=204)
    def delete_item(item_id: int) -> Response:
        get_or_404(item_id)
        del items[item_id]
        return Response(status_code=204)

    return app
```

Try it: `TestClient(create_app())` from `fastapi.testclient`. Pydantic returns
422 for invalid bodies and query values automatically.

Persistence across restarts: write the whole state to `path.with_suffix(".tmp")`,
then `tmp.replace(path)` (atomic), and load the state in `create_app(path)`.

---

## 9. pytest

```python
import httpx
import pytest


# one behaviour per test, expected value from the statement
def test_missing_user_is_none(sol):
    assert sol.get_user(client, "u_404") is None


# many cases, one test
@pytest.mark.parametrize("status, retryable", [(500, True), (503, True), (400, False)])
def test_retryable(sol, status, retryable):
    assert sol.is_retryable(status) is retryable


# the error path, and its attributes
def test_raises_on_403(sol):
    with pytest.raises(sol.ApiError) as exc:
        sol.do_thing()
    assert exc.value.status == 403


# fake HTTP server without any network: httpx.MockTransport
def test_follows_cursor():
    pages = {None: {"results": [1, 2], "next_cursor": "b"},
             "b": {"results": [3], "next_cursor": None}}
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.url.params))
        return httpx.Response(200, json=pages[request.url.params.get("cursor")])

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.test")
    assert list(iter_cursor(client, "/v1/things", headers={})) == [1, 2, 3]
    assert len(seen) == 2


# backoff without real sleeping
def test_backoff_schedule(sol, clock):          # clock is a FakeClock
    ...
    assert clock.sleeps == pytest.approx([0.5, 1.0, 2.0], rel=0.5)

# also handy: tmp_path (a fresh directory), monkeypatch.setenv("API_KEY", "x")
```

What to cover: the happy path, each rule the statement names, ordering and
tie-breaks, empty input, and each failure mode (4xx, 5xx, timeout, bad data).
Put the expected values in from the statement, never from running your code.
