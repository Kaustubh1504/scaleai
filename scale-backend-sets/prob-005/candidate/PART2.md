# Part 2: Retries with backoff, and dead-lettering (about 20 minutes)

Subscribers go down, get overloaded and sometimes reject us for good. Instead of
hammering a failing endpoint on every pass, failed deliveries are **scheduled**
for a later retry, and hopeless ones are given up on.

This replaces Part 1's "attempted again on the next call" rule. Never sleep
inside `dispatch_due()`: scheduling only sets `next_attempt_at`, and a later
call does the retry.

## Which deliveries are due

`dispatch_due()` reads `now = clock.time()` once at the start of the call and
attempts each `pending` delivery with `next_attempt_at <= now`, **at most once
per call** (even if its new `next_attempt_at` is still `<= now`). A brand-new
delivery is due immediately. Order is unchanged from Part 1.

## Classifying a failed attempt

| result of the attempt | retryable? |
|---|---|
| HTTP 408, HTTP 429, any HTTP 5xx | yes |
| `httpx.ConnectError` (connection refused or reset) | yes |
| any other non-2xx response (1xx, 3xx, other 4xx) | no |
| any other `httpx.HTTPError` | no |

* **Not retryable**: the delivery becomes `dead` immediately.
* **Retryable**: the delivery stays `pending` and is scheduled (below), unless this
  was attempt number `max_attempts` (the constructor argument, default 5); then it
  becomes `dead`. Every attempt counts, including 429s, so a delivery gets at most
  `max_attempts` attempts in total.

A `dead` delivery is never attempted again. Its `next_attempt_at` is `null`, its
`last_error` describes the final attempt, and the audit line for that final
attempt has `"outcome": "dead"`. It is counted in `DispatchReport.dead`.

## Scheduling a retry

Let `t` be `clock.time()` when attempt number `n` (1-based) was made.

* **429 with a `Retry-After` header** whose value is a non-negative integer number of
  seconds: `next_attempt_at = t + Retry-After`, exactly, even if larger than 300.
* **Otherwise** (including a 429 without a usable `Retry-After`):
  `next_attempt_at = t + min(300, 10 * 2 ** (n - 1)) * j`, where `j` is drawn
  uniformly at random from `[0.5, 1.0]` independently for each retry.

So after the first failure the retry is 5–10 s later, then 10–20 s, 20–40 s,
40–80 s, 80–160 s, then 150–300 s for every later attempt.

## Notes

* One slow or failing subscriber must not delay or block deliveries to others.
* Update your tests: the mock receiver can script any sequence, e.g.
  `receiver.script_event("evt_1", [503, "429:30", 404])`, and a `FakeClock` lets
  you jump to `next_attempt_at` with `clock.set(...)`.
