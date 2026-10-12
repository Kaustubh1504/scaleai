# 13. Handle 429 and Retry-After

You poll a labeling vendor's **Batches API** to see when your batches are
delivered. The vendor rate-limits hard and answers **429 Too Many Requests**
with a `Retry-After` header, but not always the same way: sometimes it's
seconds, sometimes an HTTP-date, sometimes it's missing or junk. Their server
clock is also an hour off from yours. Extend your retry helper to wait as
long as the server asks, and no longer.

## The API

`GET /v1/batches/{batch_id}`: `{"id": "bat_001", "state": "labeling", "tasks": 50}`,
**404** if unknown, **403** for `bat_locked`. Every response has a `Date`
header from the **server's** clock (one hour ahead of `clock.time()`).

A 429 looks like one of these:

```
HTTP/1.1 429 Too Many Requests
Date: Tue, 14 Nov 2023 23:13:20 GMT
Retry-After: 3                               <- integer seconds
Retry-After: Tue, 14 Nov 2023 23:13:32 GMT   <- HTTP-date (here: 12 s after Date)
Retry-After: soon                            <- junk
(no Retry-After at all)
```

## Setup

```python
from kit import FakeClock; from problem_api import make_api
clock = FakeClock(); api = make_api(clock); client = api.client()
api.script("GET /v1/batches/bat_001", ["429:3", api.too_many_in(12), api.too_many("soon")])
```

`api.too_many(value)` queues a 429 with `Retry-After: value` (`None` = no
header); `api.too_many_in(s)` queues one whose Retry-After is an HTTP-date `s`
seconds after the server's `Date`; `"429:N"` / `"429"` are plain 429s with no
`Date`. Use `clock.time()` / `clock.sleep()` only (tests pass a
`kit.FakeClock`, which records waits in `clock.sleeps`). The
`if __name__ == "__main__":` block is what the Run button executes: print each
429's status, `Date` and `Retry-After` there to see the raw data.

## Your task

Your module must define:

* `class ApiError(Exception)`: constructor `ApiError(status, path, attempts, message="")`;
  attributes `.status: int | None`, `.path: str`, `.attempts: int` (as in problem 12).
* `class RateLimitedError(Exception)`: constructor `RateLimitedError(path, count)`;
  attributes `.path: str`, `.count: int` (429s in the streak).
* `retry_after_seconds(retry_after: str | None, date: str | None, now: float) -> float`
* `request_respecting_429(client: httpx.Client, method: str, path: str, *, clock, rng: random.Random, max_attempts: int = 4, base_s: float = 0.5, cap_s: float = 8.0, max_429s: int = 5, **kwargs) -> httpx.Response`

**`retry_after_seconds`** turns the header values into a wait in seconds:

* A non-negative integer (`"3"`): that many seconds.
* An HTTP-date: that date minus the response's `Date` header. If `date` is
  missing or unparseable, subtract `now` instead.
* Missing, empty, junk, negative (`"-5"`), or a date in the past: **1.0**.

**`request_respecting_429`** retries like problem 12, plus:

* Send with `client.request(method, path, **kwargs)`; return the first 2xx
  whose body parses as JSON.
* On a 429, `clock.sleep(retry_after_seconds(<Retry-After>, <Date>, clock.time()))`
  (no jitter), then send again.
* 429s do **not** count toward `max_attempts`. Only the other requests do.
* More than `max_429s` 429s **in a row** for this call: raise
  `RateLimitedError(path, count)` on the one over the limit, without sleeping.
  Any other outcome (success, 5xx, transport error) resets the streak.
* Same as 12: 500/502/503/504, `httpx.TransportError` and a non-JSON 2xx body
  are transient, with backoff `rng.uniform(d / 2, d)`,
  `d = min(cap_s, base_s * 2 ** (n - 1))` after the `n`th counted attempt.
  Other 4xx raise `ApiError` immediately. When the counted attempts run out,
  raise `ApiError(last_status, path, attempts=max_attempts)`.

## Example

```python
api.script("GET /v1/batches/bat_001", ["429:2", api.too_many_in(5), api.too_many("soon")])
request_respecting_429(client, "GET", "/v1/batches/bat_001", clock=clock, rng=rng).json()
# {"id": "bat_001", ...}       clock.sleeps == [2.0, 5.0, 1.0]
```

## Constraints

* Use `clock.sleep` / `clock.time`, never the `time` module.
* Parse dates with `email.utils.parsedate_to_datetime`; don't hand-roll a date parser.

<details><summary>Hint 1</summary>

Use the server's `Date`, not your own clock, as "now" for an HTTP-date. The
two clocks disagree by an hour here, and that happens in real life too.
</details>

<details><summary>Hint 2</summary>

`parsedate_to_datetime` raises `ValueError` on junk (Python 3.12) or
`TypeError` (3.10). Catch both. `.timestamp()` gives unix seconds.
</details>

<details><summary>Hint 3</summary>

Keep two counters: counted attempts (for `max_attempts`) and the current 429
streak. A 429 bumps only the streak; anything else resets the streak.
</details>

## Follow-up (talk it through)

* The server says `Retry-After: 3600`. Should your job really sleep an hour?
  What would you cap it at, and what would you do instead?
* Ten workers share one API key and all get a 429 at once. What goes wrong if
  they all wake up exactly when told to?
* Why does honouring `Retry-After` beat exponential backoff for 429s?
