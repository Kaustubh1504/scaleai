# Part 2: Per-tenant rate limits (about 20 minutes)

A single tenant's batch job is flooding the intake. Limit task creation per
tenant with a **token bucket** sized by the tenant's plan.

## The bucket

Each tenant has its own bucket, using the plan from the config
(`burst`, `refill_per_s`):

* It starts full: `burst` tokens.
* It refills continuously at `refill_per_s` tokens per second of `clock.time()`,
  never above `burst`. Fractional tokens count (after 0.5 s at 1 token/s there
  is half a token).
* Creating a task costs **1 token** and needs at least 1 whole token available.
* Tenants are isolated: one tenant's traffic never affects another's bucket.

Only `POST /tasks` is limited. GETs are free.

## Where the limit applies

The order of checks from Part 1 becomes:

1. tenant header (400 / 403)
2. `Idempotency-Key` format (400)
3. body validation (422)
4. idempotency: replay (201 + `Idempotent-Replayed: true`) or mismatch (409)
5. **rate limit (429)**
6. create the task (201): this is the only step that consumes a token

So idempotent replays and every rejected request (400, 403, 409, 422, 429)
cost nothing, and a replay is still served when the bucket is empty. A 429 is
an error, so it is not recorded under the `Idempotency-Key`: retrying the same
request later with the same key creates the task.

## Over the limit: **429**

* JSON body with a `detail` string.
* Header `Retry-After`: the number of seconds until the bucket holds 1 whole
  token, **rounded up** to an integer, and at least `1`.
  Example: `refill_per_s = 0.25` and 0.0 tokens: `Retry-After: 4`; with 0.875
  tokens: `Retry-After: 1`.

Write tests that drive the bucket with `FakeClock` (`clock.advance(seconds)`),
never with real sleeps.
