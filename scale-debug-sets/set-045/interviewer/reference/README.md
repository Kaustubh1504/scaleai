# Quote Cache Replay

Pricing quotes come from a slow origin service, so a TTL cache sits in front of it. This
tool replays a recorded trace of quote requests through the cache, applies each tenant's
discount to the quote it receives, and reports cache behaviour, per-tenant spend and the
requests that were served an out-of-date price.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/config.json`: `ttl_seconds` per model, `default_ttl_seconds`, `default_region`
  and `discounts` per tenant (a fraction: `0.1` = 10% off).
- `data/prices.csv`: the origin's price history: `model`, `region`, `price`,
  `effective_from`.
- `data/requests.csv`: the trace: `request_id`, `at`, `tenant`, `model`, `region`. It is
  in chronological order.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Tenants, models and regions: trim and lower-case. A blank region means
  `default_region`.
- Times use one of `2026-08-01 10:00:00`, `08/01/2026 10:00:00` (month/day/year) or
  `2026-08-01T10:00:00`.

### Origin

1. The origin price for (model, region) at time `t` is the price of the row with the
   latest `effective_from` that is at or before `t`. Prices differ by region.
2. Every origin lookup made by the cache on a miss counts as one origin call.

### Cache

3. Cached values are keyed by everything that changes the origin price: model **and**
   region. Tenants share entries, since the discount is applied after the lookup.
4. A model's TTL is `ttl_seconds[model]`, or `default_ttl_seconds` if the model is not
   listed. A TTL of `0` means the model is **never cached**: every request is a miss.
5. An entry stored at `t` with TTL `s` is fresh for requests strictly before `t + s`.
   At exactly `t + s` it has expired: that request is a miss and refetches.
6. On a miss the fetched value is cached (if the TTL is above 0) as of the request time.

### Quotes

7. The quoted price = base price × (1 − tenant discount), rounded to 4 decimals. Tenants
   not in `discounts` pay the base price. Applying a discount must never change what is
   stored in the cache.
8. A request is **stale** when the base price it was served differs from the origin price
   at that request's time.

### Report

`cachekit.report.build_report()` returns:

- `requests`: request id → `hit` (bool) and `price` (the quoted price);
- `tenants`: tenant → `requests`, `hits`, `spend` (sum of quoted prices, 4 decimals);
- `origin_calls`: number of origin calls;
- `stale_served`: ids of stale requests, in trace order.

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # print the report
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
