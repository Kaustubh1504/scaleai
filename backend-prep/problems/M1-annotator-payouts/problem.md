# M1. Annotator payouts

Annotators on the labeling platform are paid every two weeks for the work that
passed review. Finance wants a job that pulls everything from the platform API,
works out what each annotator earned in a pay period, and (in Part 3) pays
them. Money is involved: every rule below is exact, and amounts are **integer
cents** throughout.

## The API

`POST /oauth/token` with JSON `{"client_id": ..., "client_secret": ...}` returns
`{"access_token": "tok_00001", "token_type": "bearer", "expires_in": 3600}`.
Wrong credentials are **401**. Every `/v1` request needs
`Authorization: Bearer <access_token>`; a missing or expired token is **401**.

Each collection paginates differently:

| Endpoint | Params | Envelope |
|---|---|---|
| `GET /v1/annotators` | `page` (1-based), `per_page` (1..25) | `{"data": [...], "page", "per_page", "total", "total_pages"}` |
| `GET /v1/tasks` | `offset` (≥ 0), `limit` (1..50) | `{"items": [...], "offset", "limit", "total"}` |
| `GET /v1/submissions` | `cursor` (opaque, omit at first), `limit` (1..50) | `{"results": [...], "next_cursor": str \| null}` |

Out-of-range params are **400**. Records (clean form):

```json
{"id": "ann_001", "name": "Ana", "on_hold": false}
{"id": "task_001", "project": "chat-ranking", "reward_cents": 25}
{"id": "sub_0002", "annotator_id": "ann_001", "task_id": "task_002",
 "submitted_at": "2024-05-03T10:15:00Z",
 "reviews": [{"id": "rev_0002", "verdict": "rejected", "reviewed_at": "2024-05-04T09:00:00Z"},
             {"id": "rev_0003", "verdict": "approved", "reviewed_at": "2024-05-05T09:00:00Z"}]}
```

## Part 1: compute the payouts (about 20 minutes)

### Setup

```python
from problem_api import CLIENT_ID, CLIENT_SECRET, make_api   # also: sample_data, messy_sample_data
api = make_api(); http = api.client()                         # httpx.Client, base_url already set
```

Tests build `PayoutClient(api.client(), CLIENT_ID, CLIENT_SECRET, clock=api.clock, rng=random.Random(seed))`.
Your file starts empty; the `if __name__ == "__main__":` block is what the Run button executes (use it to look at the raw responses).

### Contract (Part 1)

* `class ApiError(Exception)` — `ApiError(status: int, path: str, message: str = "")`; attributes `.status`, `.path`.
* `class AuthError(ApiError)` — the token could not be obtained.
* `class PayoutClient` — `__init__(self, http: httpx.Client, client_id: str, client_secret: str, *, clock=None, rng: random.Random | None = None)`; defaults: `kit.RealClock()` and `random.Random()`.
* `PayoutClient.annotators() / .tasks() / .submissions() -> list[dict]` — every record, API order.
* `compute_payouts(client: PayoutClient, period_start: datetime, period_end: datetime) -> dict` — the report below.
* `report["period"]` is `f"{start:%Y-%m-%dT%H:%M:%SZ}/{end:%Y-%m-%dT%H:%M:%SZ}"`, e.g. `"2024-05-01T00:00:00Z/2024-05-15T00:00:00Z"`.

* Send every request through `http` (its `base_url` is set). Get a token on the
  first `/v1` request and reuse it. `clock` and `rng` are for Part 3.
* A non-2xx token response raises `AuthError`; any other non-2xx response raises
  `ApiError` with `.status` and `.path` (e.g. `"/v1/tasks"`).
* Follow each collection's pagination to the end.
* **Period**: a submission is in the period when
  `period_start <= submitted_at < period_end` (UTC, end exclusive).
* **Verdict**: the verdict of the submission's **latest review** (greatest
  `reviewed_at`; on a tie, the greatest review `id` as a string). No reviews
  means **pending**. A review made after `period_end` still counts.
* **Earnings**: each approved submission earns its task's `reward_cents`.
  Rejected and pending earn nothing.

The report (keys `period`, `rows`, `total_cents`):

```python
{"period": "2024-05-01T00:00:00Z/2024-05-15T00:00:00Z", "total_cents": 130,
 "rows": [{"annotator_id": "ann_001", "name": "Ana", "approved": 2, "rejected": 0, "pending": 0, "amount_cents": 65}, ...]}
```

* One row per annotator with **at least one submission in the period**, sorted
  by `annotator_id`. `approved + rejected + pending` = their submissions in the period.
* `total_cents` is the sum of `amount_cents` over the rows.

**Example** (`make_api()`, period 2024-05-01 to 2024-05-15): `ann_001` 2 approved
→ 65; `ann_002` 1 rejected (tie on `reviewed_at`, `rev_0005` wins) + 1 pending →
0; `ann_003` 1 approved → 30 (`sub_0006` at exactly `period_end` is out);
`ann_004` has no row; `ann_005` → 35; `ann_006` → 0. `total_cents` = 130.

<!-- part 2 -->

## Part 2: the real data is messy (about 20 minutes)

The production API is fed by three generations of clients. Parse defensively:

* **Timestamps** (`submitted_at`, `reviewed_at`) may be:
  * ISO 8601 `YYYY-MM-DDTHH:MM:SS[.ffffff]` with `Z`, a `±HH:MM` offset, or no
    offset (means UTC); a space may replace the `T`;
  * an epoch number (int or float), or a string of ASCII digits: if its value is
    `≥ 10**11` it is **milliseconds**, otherwise **seconds**.
  * Anything else (`null`, `"yesterday"`, `""`, ...) is unparseable.
* A submission with an unparseable `submitted_at` is left out of every count; its
  id goes in `invalid_submissions`. A review with an unparseable `reviewed_at`
  is ignored.
* **Verdicts** are case- and whitespace-insensitive (`" Approved "` is approved).
  A review whose verdict is not approved/rejected after that is ignored (an
  ignored review can't be the latest one).
* **reward_cents** is known when it is an `int` ≥ 0 (not a bool) or a string of
  ASCII digits after stripping whitespace (`" 25 "` → 25). Anything else
  (`null`, missing, `"N/A"`, `12.5`, `-5`), or a `task_id` with no task, is
  **unknown**: the approved submission still counts as approved, earns 0, and its
  id goes in `unknown_reward`.
* **on_hold** is false only for `false`, `null`/missing, `0`, or a string that is
  `"false"`, `"no"` or `"0"` (case-insensitive, stripped). Every other value
  means **on hold** (when in doubt, don't pay).
* The same submission `id` can be served twice: count its first occurrence only.

### Contract (Part 2)

No new names; the report gains keys (on clean data the lists are empty and `held_cents` is 0):

* every row gains `"on_hold": bool`; on-hold annotators still get a row with their real counts and `amount_cents`.
* `total_cents` — sum of `amount_cents` over rows **not** on hold.
* `held_cents` — sum of `amount_cents` over rows on hold.
* `unknown_reward` — submission ids, sorted (approved submissions only).
* `invalid_submissions` — submission ids, sorted.

<!-- part 3 -->

## Part 3: pay them, safely (about 20 minutes)

The API is having a bad week, and a payout must never be sent twice.

**Retries** (every request: token, GETs and POSTs):

* Transient: HTTP 500/502/503/504, any `httpx.TransportError`, or a 2xx whose
  body is not valid JSON. A request gets at most **4 attempts**. Before attempt
  `n + 1` call `clock.sleep(rng.uniform(d / 2, d))` with
  `d = min(8, 0.5 * 2 ** (n - 1))`. When attempts run out raise `ApiError`
  (`AuthError` for the token request) with the last HTTP status, or 0 if the
  last attempt was a transport error or bad JSON.
* **429**: `clock.sleep(float(Retry-After))` (1 if missing) and send again. 429s
  don't use attempts, but the **10th 429 in a row** raises `ApiError(429)`.
* Other 4xx are not retried.
* **Token expiry**: on a 401 from a `/v1` request, get a new token and send the
  request once more (not an attempt). A second 401 in a row raises `AuthError`.

### Contract (Part 3)

* `publish_payouts(client: PayoutClient, report: dict) -> dict` — returns `{"paid": [annotator_id, ...], "failed": [annotator_id, ...]}`, both in row order.
* Retries apply inside `PayoutClient` (all requests), using its `clock` and `rng`.

**Publishing**:

* A row is payable when `on_hold` is false and `amount_cents > 0`. For each
  payable row, in row order: `POST /v1/payouts` with JSON
  `{"annotator_id", "period": report["period"], "amount_cents"}` and header
  `Idempotency-Key: <period>:<annotator_id>`.
* `201` (created) and `200` (the server already had that key) mean **paid**.
* If the POST still fails (attempts exhausted or a 4xx such as 409), the
  annotator goes in `failed` and you carry on. `AuthError` propagates.
* Running the same report twice must not create a single new payout.
* Note: a `"malformed"` reply to a POST means the server **stored** the payout
  but you never saw the answer.

## Constraints

* HTTP only (don't read `api.data`). Use `clock.sleep`, never `time.sleep`.
* No floats in money. Tests use `kit.FakeClock` and a seeded `random.Random`.

<details><summary>Hint 1</summary>

Write one private `_send(method, path, **kw)` that owns the retry loop and
returns the final response; put the token/401 logic one layer above it, and the
three paginators above that. Each layer stays under 25 lines.
</details>

<details><summary>Hint 2</summary>

Python 3.10's `datetime.fromisoformat` rejects a trailing `Z`: replace it with
`+00:00`. Use `.astimezone(timezone.utc)` for offsets and `.replace(tzinfo=...)`
for naive values.
</details>

## Discussion (talk it through)

* What exactly does the idempotency key guarantee? What happens if finance
  corrects a reward and re-runs the same period: who gets paid what, and how
  would you design the key and the API for corrections?
* Why is "unknown means held / unknown reward means 0 + report it" the right
  default for money? How would you alert when `unknown_reward` suddenly grows?
* The crawl takes 40 minutes and a review lands mid-crawl. Which numbers can be
  wrong, and how would you make a run reproducible (snapshot / `as_of`)?
