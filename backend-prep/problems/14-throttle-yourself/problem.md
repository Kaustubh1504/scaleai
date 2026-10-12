# 14. Throttle yourself: rate-limit headers and a token bucket

The **Annotations API** allows **5 requests per second** per key. Every 429
you trigger counts against your account, and enough of them get the key
suspended. Retrying after a 429 (problem 13) is too late. Your client should
**never cause one**. The server tells you where you stand on every response,
so use that. You'll also build a client-side token bucket for APIs that
don't send those headers.

## The API

`GET /v1/annotations/{ann_id}`: `{"id": "ann_001", "label": "dog", "annotator": "usr_01"}`, or 404.

Every response, including 404s and 429s, carries:

```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0          <- requests left in the current window (after this one)
X-RateLimit-Reset: 1700000001     <- unix seconds when the window resets
```

Windows are fixed: `[1700000000, 1700000001)`, `[1700000001, 1700000002)`, ...

## Setup

```python
from kit import FakeClock; from problem_api import make_api
clock = FakeClock(); api = make_api(clock); client = api.client()   # 5 req/s
```

`make_api(clock, limit=5, window_s=1.0, latency_s=0.0)`; `latency_s` advances
the clock on every request. Use `clock.time()` / `clock.sleep()` only (tests
pass a `kit.FakeClock`, which records waits in `clock.sleeps`). The
`if __name__ == "__main__":` block is what the Run button executes: fire a
few unthrottled requests there and print the `X-RateLimit-*` headers.

## Your task

Your module must define:

* `class ThrottledClient`: `ThrottledClient(client: httpx.Client, clock)`
  * `.request(method: str, path: str, **kwargs) -> httpx.Response`
  * `.get(path: str, **kwargs) -> httpx.Response`: same as `request("GET", path, **kwargs)`
* `class TokenBucket`: `TokenBucket(rate_per_s: float, burst: int, clock)`
  (tests pass these as keywords)
  * `.acquire() -> None`

**ThrottledClient**

* Sends through `client.request(method, path, **kwargs)` and returns the
  response unchanged (status codes included; it doesn't raise or retry).
* After each response, remember its `X-RateLimit-Remaining` and
  `X-RateLimit-Reset`.
* Before a request: if the last `Remaining` was `0` and `clock.time()` is
  before `Reset`, `clock.sleep(reset - clock.time())`. Otherwise send right away.
* Never sleep when you don't have to: no fixed pacing, no padding. Never
  sleep a zero or negative duration.

**TokenBucket**

* Starts **full** with `burst` tokens and refills continuously at `rate_per_s`
  tokens per second (fractions count), never above `burst`.
* `acquire()` takes one token. If at least one is available, take it without
  sleeping. Otherwise sleep exactly the deficit, `(1 - tokens) / rate_per_s`
  seconds, then take it (leaving 0).

## Example

```python
api = make_api(clock)                  # 5 req/s, clock starts at 1700000000.0
tc = ThrottledClient(api.client(), clock)
for i in range(1, 51):
    tc.get(f"/v1/annotations/ann_{i:03d}")
api.limiter.rejected     # 0
clock.sleeps             # [1.0] * 9: 10 windows of 5, one wait between each

b = TokenBucket(rate_per_s=2, burst=3, clock=clock2)
for _ in range(5): b.acquire()
clock2.sleeps            # [0.5, 0.5]: the first 3 are free
```

## Constraints

* Use `clock.time()` / `clock.sleep()`, never the `time` module.
* Don't read `api.limiter`. Go by the headers.

<details><summary>Hint 1</summary>

The client only needs two attributes, `_remaining` and `_reset`, set from the
headers of the last response. Parse them with `int()` and `float()`.
</details>

<details><summary>Hint 2</summary>

For the bucket, store `tokens` and the time you last refilled. On every
`acquire`, first add `(now - last) * rate` tokens (capped at `burst`).
</details>

## Follow-up (talk it through)

* Ten worker processes share one API key. Why does per-process throttling
  break, and what would you use instead?
* A token bucket with `rate=5, burst=5` can still get 429s from this
  fixed-window server. Construct the sequence. How would you configure it to be safe?
* Header-driven vs client-side throttling: when do you need each?
