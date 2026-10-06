# Part 3: Surviving a flaky, rate-limited API (about 20 minutes)

The provider is having a bad week: transient 5xx errors, slow responses, the
occasional truncated body, and a strict rate limit. The nightly report must
still come out right, without hammering the API.

## Retries (apply to every request, including token requests)

* Every request uses `timeout=10` seconds.
* **Transient failures**: HTTP 500, 502, 503, any `httpx.TransportError`
  (including timeouts), and a 2xx response whose body is not valid JSON.
  A request gets at most **4 attempts**. Before attempt `n + 1` wait (with
  `clock.sleep`) a random duration uniformly drawn from `[d / 2, d]` where
  `d = min(8, 0.5 * 2 ** (n - 1))` seconds. If all 4 attempts fail, raise
  `ApiError`.
* **429**: wait exactly what `Retry-After` says, then send the request again.
  The header is either a number of seconds or an HTTP date; for a date, the wait
  is that date minus the response's `Date` header. If the header is missing,
  wait 1 second. 429s do **not** use up the 4 attempts, but after **10** 429s
  in a row for the same request, raise `ApiError`.
* Other 4xx responses are not retried (except the single 401 retry from Part 2).

## Efficiency

* Request projects with `per_page=10` and tasks with `limit=25`.
* Fetch each page once. The only repeated requests allowed are retries of a
  request that failed.

## Discussion (no code required)

Be ready to talk about:

* crawling 10,000 projects within a rate limit: concurrency, and sharing one
  limit across workers;
* data changing while you crawl: what cursor vs page-number pagination
  guarantees, and how you would make the report a consistent snapshot;
* making the nightly job incremental instead of re-reading everything.
