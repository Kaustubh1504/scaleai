# prob-003 — Idempotent Task Intake with Tenant Rate Limits (interviewer notes)

**Mimics:** the "build a small production API, then harden it" shape of the real
round. The follow-ups it sets up are the reported ones: rate limiting and scaling
to many instances.
**Difficulty:** medium · **Mode:** FastAPI · **Starter:** minimal skeleton · **Planted bugs:** none

## Setup

```bash
python tools/export_candidate.py prob-003 ~/interview --part1-only   # give the candidate prob-003/
# afterwards, from scale-backend-sets/:
SOLUTION_DIR=~/interview/prob-003 python -m pytest prob-003/interviewer/hidden_tests -q
SOLUTION_DIR=... python -m pytest prob-003/interviewer/hidden_tests/test_part2.py -m "not change"   # change not delivered
```

The hidden tests build the app with `create_app(storage_dir=tmp, clock=FakeClock(), tenants=CONFIG)`.
`CONFIG` is defined in `hidden_tests/conftest.py` and adds a third plan
(`tiny`: burst 2, 0.25 tokens/s) that the candidate has never seen, so a solution
that hard-codes `free`/`pro` numbers fails Part 2. Candidate edits to `data/`
cannot change the outcome. If the candidate renamed `create_app` or moved it, fix
the import in a scratch copy rather than failing them outright.

Part 3 concurrency tests start 10 threads behind a `threading.Barrier`, each with
its own `TestClient` over **one** app. (Starlette's `TestClient` opens a fresh
event-loop thread per request when not used as a context manager, so a shared
client would behave the same; one per thread just makes it explicit.) A
check-then-create without a lock fails these tests in practice on every run; the
reference passed 50/50 runs in a loop.

## Timeline

### 60-minute mode

| min | what happens |
|---|---|
| 0–3 | Hand over `PART1.md`. Candidate reads `app/main.py`, `data/tenants.json`, `data/sample_requests.jsonl`. |
| 3–12 | Tenant dependency, key validation, pydantic model with strict fields, create + GET. |
| 12–20 | Idempotency: fingerprint, replay header, 409, per-tenant scoping, tests. Reveal `PART2.md` once replay works. |
| 20–30 | Part 2: token bucket against `clock.time()`, 429 + `Retry-After`, ordering vs replay. |
| ~30 | **Drop the mid-part change** (below), once a 429 test passes. |
| 30–40 | `X-RateLimit-Remaining`, tests with `clock.advance`. Reveal `PART3.md`. |
| 40–55 | Part 3: persistence (sqlite or atomic JSON), restart test, lock for concurrent retries, 24 h expiry. |
| 55–60 | Follow-up discussion (pick 1–2 of the questions below). |

If the candidate is behind at minute 22, reveal Part 2 anyway and let the
canonical-body edge cases go. If they are behind at minute 45, take persistence
only (restart test) and discuss concurrency and expiry.

### 30-minute mode (Part 1 plus the start of Part 2)

| min | what happens |
|---|---|
| 0–2 | Hand over `PART1.md`. |
| 2–18 | Validation, create/GET/list, idempotent replay + 409. |
| 18–20 | Reveal `PART2.md`. |
| 20–27 | Token bucket + 429 with `Retry-After`, ideally one `FakeClock` test. Skip the mid-part change. |
| 27–30 | One follow-up question (#1 below). |

Score Part 3 categories as "not observed"; run `test_part1.py` and
`test_part2.py -m "not change"`.

## Mid-part requirement change (Part 2, ~minute 30)

Say, verbatim:

> "Clients want to see their budget. Every 201 and every 429 from `POST /tasks`,
> including idempotent replays, must carry `X-RateLimit-Remaining`: the number of
> whole tokens left in the tenant's bucket after the request, rounded down. A
> replay doesn't spend a token but still refills the bucket, so it reports the
> current balance. Other error responses may leave the header out."

What it tests: whether the bucket is an object you can query
(`remaining()`/`peek()`) or a single `allow()` boolean buried in the handler.
It also tests whether the candidate rounds correctly: `floor`, not `round`, and
after `try_acquire` rather than before. Strong candidates return a decision object
(`allowed, remaining, retry_after`) and set all three headers in one place.
Hidden tests: `test_part2.py::test_remaining_header_*` (marker `change`).

(Why only 201/429 and not every response: candidates who let FastAPI produce
the 422 would otherwise have to write a custom exception handler. That tests
framework trivia, not the rate limiter. If the candidate asks about 409/422,
"your call, the tests don't check it" is the answer.)

## Planted bugs

None. This is a skeleton problem.

## Hint ladder

Give the lowest hint that unblocks; note each hint in the rubric.

**Part 1**
1. "Send a request with no tenant header and a broken body. What status do you get, and what does the spec say?" (FastAPI validates a pydantic body parameter before the handler runs, so they get 422 instead of 400.)
2. "FastAPI runs dependencies before it validates the body, or you can read `await request.body()` and call `TaskIn.model_validate_json` yourself. Either gives you control of the order."
3. "What exactly do you compare to decide 'same body'? Try `json.dumps(model.model_dump(), sort_keys=True)`."

**Part 2**
1. "Which time source does your bucket use? Can a test move it?" (must be `clock.time()`, never `time.time()`)
2. "Do you need a background refill loop, or can you compute the tokens from the time elapsed since the last update?" (lazy refill: `tokens = min(burst, tokens + dt * rate)`)
3. "Write down the order of checks from the spec as five lines of code before you write the bucket. Where does `try_acquire` go relative to the replay lookup?"

**Part 3**
1. "Kill the app (make a new `create_app` over the same directory). What does it still know?"
2. "Two threads both see 'no record for this key'. What happens next? What makes check-and-create one step?" (a `threading.Lock`, or a unique constraint in sqlite)
3. "Where does the 24 h come from: the record's creation time, or the last time it was used?"

## Common pitfalls (what the hidden tests catch)

* Pydantic body parameter, so a missing tenant header plus a bad body gives 422 instead of 400 (`test_order_of_checks`).
* Lax pydantic: `"3"`, `3.0` and `true` accepted as priority; unknown fields silently dropped.
* Fingerprinting the raw request bytes, so key order or an explicit `"priority": 5` causes a 409.
* Global idempotency keys (not scoped per tenant), or `GET /tasks/{id}` leaking other tenants' tasks (should be 404, not 403).
* Recording a 422/429 under the key, so the retry after a 429 replays the error forever.
* Rate-limiting before the replay lookup, so replays spend tokens or get 429.
* `Retry-After` computed with `round()` or `int()` instead of `ceil`, or `0` when nearly refilled.
* Refill not capped at `burst`, or the bucket starting empty.
* Hard-coding the `free`/`pro` numbers instead of reading the plan (`tiny` plan in the hidden config).
* No lock: check-then-create races, 2+ tasks for one key under 10 threads.
* A lock in the rate limiter but not around the whole check → acquire → create sequence.
* TTL measured from the last replay (sliding) instead of from creation; `<=` vs `<` at exactly 24 h.
* Not atomic: writing the JSON file in place (not a hidden test, but ask "what if we crash mid-write?").

## Follow-up questions

**1. "We run 30 instances of this API behind a load balancer. How do the per-tenant limits still hold?"**
A strong answer covers: local buckets let a tenant use 30× the plan. Options:
a central store (Redis) with an atomic token-bucket script (Lua / `EVALSHA`)
keyed by tenant, holding tokens and a timestamp, using Redis server time rather than each
instance's clock; the cost is a network hop per request, so handle Redis being down
(fail open for reads vs fail closed for writes: a product decision); approximate
alternatives: split the budget per instance (`rate/N`, rebalanced as N changes),
or local buckets that sync deltas every 100 ms (bounded overshoot); sticky
routing by tenant at the load balancer; limits applied at the API gateway; returning
`Retry-After` consistently; metrics on 429 rate per tenant.

**2. "Idempotency records at scale: 50 tenants, 10k requests/s. What do you store, where, and for how long?"**
Strong: store `(tenant, key) → fingerprint (hash of canonical body), status,
response body (or task id), created_at, state (in_progress|done)` in a store
with native TTL (Redis `SET NX EX`, DynamoDB TTL, or a Postgres table with an
index on `created_at` and a periodic purge); 24 h is a contract with clients,
so publish it; key cardinality ≈ requests/day (~860M/day here), so store a hash
of the response or a task id rather than large bodies; scope keys by tenant to
avoid collisions and cross-tenant leaks; cap key length (the 64-char rule);
store a fingerprint hash, not the raw body (size and PII); decide what a
replay of a 5xx should do (usually don't record 5xx, so the retry re-executes).

**3. "The process crashes after the task is created but before the idempotency record is saved. What happens on the client's retry, and how do you prevent it?"**
Strong: the retry sees no record and creates a duplicate task: exactly the
failure idempotency was meant to prevent. Fixes: write both in **one transaction**
(the reference does this in sqlite); or write the record first as
`in_progress` (`INSERT … ON CONFLICT DO NOTHING` / `SET NX`) and then the task,
then mark it done. A crash leaves an `in_progress` record, so retries get 409
"in progress" until a lease expires and recovery can check whether the task
exists; or derive the task id deterministically from `(tenant, key)` so a
re-run upserts the same task. Bonus: the outbox pattern if task creation also
publishes an event; the same reasoning applies to the token bucket (a token
spent on a request that then failed, which is acceptable).

## Reference solution

`reference/app/`: `models.py` (strict `TaskIn`, key regex, canonical-JSON
`fingerprint()`), `config.py` (plans/tenants parsed and validated at startup),
`ratelimit.py` (lazy-refill token bucket per tenant on the injected clock, one
lock, epsilon-safe floor/ceil, a `Decision(allowed, remaining, retry_after)`),
`store.py` (sqlite, opened lazily so importing `app.main` touches no disk; a task
and its idempotency record in one transaction; the `(tenant_id, key)` primary key
makes a second writer fail with `KeyTaken` even from another process),
`intake.py` (the ordered decision: replay/409 → rate limit → create, under one
lock; 24 h TTL from creation), and `main.py` (dependencies for tenant and key so
they run before body validation, then `model_validate_json` on the raw body).

Lines the candidate must add (verifier count, docstrings included): **268** in
total. By part: Part 1 ≈ 100 (model + fingerprint 17, routes and dependencies
≈ 50, in-memory store and idempotency ≈ 30); Part 2 ≈ 65 (bucket 36, config 28,
the change ≈ 5); Part 3 ≈ 100 (sqlite store replacing the in-memory one ≈ 80,
lock, expiry and race handling ≈ 20) plus discussion. A JSON-files store with
temp-file + `os.replace` and an in-memory index loaded at startup is an equally
good Part 3 answer, about the same size.
