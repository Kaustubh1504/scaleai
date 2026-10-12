# M3. Org chart crawler

An enterprise customer wants seat-based billing per department. Their HR
system exposes the org chart as linked resources: each org lists its child
orgs, and members are a separate paginated collection. The data is years old:
there are cycles, orgs listed under two parents, and links to orgs that were
deleted. You need a crawler that computes **headcount per org subtree**, and
that keeps going through expiring tokens, permission holes, rate limits and
crashes.

## The API

| Request | Response |
|---|---|
| `GET /v1/orgs/{org_id}` | `{"id": "org_eng", "name": "Engineering", "children": ["org_platform", "org_ml"]}` |
| `GET /v1/orgs/{org_id}/members?limit=1..50&cursor=...` | `{"results": [{"person_id": "p003", "name": "...", "role": "ic"}], "next_cursor": str \| null}` |
| `POST /oauth/token` `{"client_id", "client_secret"}` | `{"access_token": "tok_00001", "token_type": "bearer", "expires_in": 20}` |

An unknown org is **404** (on both org endpoints). Omit `cursor` on the first
members page; out-of-range `limit` is **400**.

## Part 1: crawl and count (about 20 minutes)

### Setup

```python
from problem_api import CLIENT_ID, CLIENT_SECRET, make_api   # also: kit.FakeClock
api = make_api(); http = api.client()                         # Part 2: make_api(auth=True, token_ttl_s=20, latency_s=1.0, clock=clock); Part 3: rate_limit=3
```

Tests build `OrgClient(api.client(), CLIENT_ID, CLIENT_SECRET, clock=api.clock)`.
Your file starts empty; the `if __name__ == "__main__":` block is what the Run button executes (walk a few links by hand first).

### Contract (Part 1)

* `class ApiError(Exception)` — `ApiError(status: int, path: str, message: str = "")`; attributes `.status`, `.path` (e.g. `"/v1/orgs/org_ops/members"`).
* `@dataclass class CrawlResult` — fields `order: list[str]` (crawled orgs, BFS order), `headcount: dict[str, int]` (org id → distinct people in its subtree), `dangling: list[str]` (referenced ids that 404, sorted), `inaccessible: list[str]` (Part 2; `[]` for now).
* `class OrgClient` — `__init__(self, http: httpx.Client, client_id: str, client_secret: str, *, clock=None)`; default clock `kit.RealClock()`.
* `crawl_org(client: OrgClient, root_id: str, checkpoint_path: str | Path | None = None) -> CrawlResult` — `checkpoint_path` is Part 3.
* Suggested (not tested directly): `OrgClient.get(path, params=None) -> Any` returns the JSON body and raises `ApiError` on non-2xx; later parts add auth and rate limiting there.

In Part 1 the API needs no auth (Part 2 adds it).

* **BFS** from `root_id`: visit orgs level by level, children in the order
  they're listed. Each org is requested **once** (`GET /v1/orgs/{id}` once, and
  every members page once), even with cycles or several parents.
* A **crawled** org is one whose record and **all** member pages were fetched.
  `order` lists crawled orgs in the order they were visited.
* A child that returns **404** is **dangling**: record it and carry on. If the
  root itself fails, or any other error occurs, raise `ApiError`.
* **Subtree** of org X: X plus every crawled org reachable from X by following
  `children` (cycles included, so two orgs in a cycle share a subtree).
* `headcount[X]` = the number of distinct `person_id`s that are members of any
  org in X's subtree (a person in two orgs counts once). One key per crawled org.

**Example** (`make_api()`, root `org_root`):

```
order      = [org_root, org_eng, org_ops, org_platform, org_ml, org_support, org_legal, org_research]
headcount  = {org_root: 46, org_eng: 16, org_ops: 28, org_platform: 9, org_ml: 14,
              org_support: 25, org_legal: 2, org_research: 14}
dangling   = [org_legacy]
```

`org_ml` → `org_research` → `org_ml` is a cycle, so both count 14; `p005` is in
both `org_eng` and `org_platform` and counts once for `org_eng`.

<!-- part 2 -->

## Part 2: tokens that expire, orgs you can't see (about 20 minutes)

The API now requires `Authorization: Bearer <token>` on every `/v1` request.
Tokens live `expires_in` seconds (20 in production) and the crawl is slow, so
they expire mid-crawl. Some orgs are confidential.

### Contract (Part 2)

* `class AuthError(ApiError)` — the token could not be obtained, or a request got 401 twice.

* Get a token with `POST /oauth/token` (JSON body with your credentials) before
  the first `/v1` request. A non-2xx token response raises `AuthError`.
* **Proactive refresh**: the token expires at `t + expires_in`, where `t` is
  `clock.time()` when you got it. Before each `/v1` request, if
  `clock.time() >= expires_at - 5`, get a new token first.
* **Reactive refresh**: if a `/v1` request still gets **401** (tokens can be
  revoked), get a new token and send the request once more. A second 401 for
  that request raises `AuthError`.
* **403** on `GET /v1/orgs/{id}`: the org is **inaccessible**. Record it (sorted
  ids in `inaccessible`), don't crawl through it, carry on. It is not in `order`
  or `headcount`. (A 403 on the root raises `ApiError`.)

<!-- part 3 -->

## Part 3: rate limits and crashes (about 20 minutes)

The API allows a few requests per second. Every `/v1` response carries
`X-RateLimit-Limit`, `X-RateLimit-Remaining` (requests left in this window) and
`X-RateLimit-Reset` (Unix time, possibly fractional, when the window resets).

### Contract (Part 3)

No new names: `crawl_org(..., checkpoint_path=...)` now uses the checkpoint.

* **Never trigger a 429**: after a `/v1` response with `X-RateLimit-Remaining: 0`,
  wait until `X-RateLimit-Reset` (`clock.sleep(reset - clock.time())`, only if
  positive) before the next `/v1` request. Don't sleep otherwise.
* If you still get a **429**, `clock.sleep(float(Retry-After))` (1 if missing)
  and resend. The 5th 429 in a row for one request raises `ApiError(429)`.
* **Checkpoint**: when `checkpoint_path` is given, after each org is finished
  (crawled, dangling or inaccessible) write the whole crawl state there as JSON,
  atomically (temporary file in the same directory, then `os.replace`).
* **Resume**: if the checkpoint exists when `crawl_org` starts, continue from it:
  finished orgs are not requested again, and the result is identical to an
  uninterrupted crawl (same `order`, `headcount`, `dangling`, `inaccessible`).
  An org that was half done when the process died is fetched again from scratch.
* When the crawl completes, delete the checkpoint file.
* Errors (and crashes) still propagate; the checkpoint on disk must stay valid JSON.

## Constraints

* HTTP only; use `clock.time()` / `clock.sleep()`, never the `time` module.
* Tests use `kit.FakeClock` with a per-request latency, so time moves as you crawl.

<details><summary>Hint 1</summary>

Keep the crawl state in one dict (`queue`, `seen`, `order`, `children`,
`members`, `dangling`, `inaccessible`): checkpointing becomes `json.dumps(state)`
and resuming becomes `json.loads`. Peek at `queue[0]` and pop it only after the
org is finished.
</details>

<details><summary>Hint 2</summary>

All three Part 2/3 concerns live in `OrgClient.get`: wait for the rate limit,
make sure the token is fresh, send, remember the rate-limit headers, then
handle 429 / 401 / errors. The crawler never sees them.
</details>

## Discussion (talk it through)

* Your crawler is single-threaded. How would you parallelise it while keeping
  zero 429s? What does a shared limiter look like across 10 worker processes?
* The org chart changes while you crawl (an org moves under a new parent). What
  can your numbers get wrong, and how would you get a consistent snapshot?
* Proactive vs reactive token refresh: why do you want both? What goes wrong
  with clock skew between you and the auth server?
