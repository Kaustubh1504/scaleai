# Price Quote Cache

A TTL cache sits in front of a slow pricing service. This tool replays a two-day request
log (plus a log of cache invalidations) through the cache and reports what each request
got back and how well the cache did.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/ttl.json`: TTL in seconds per endpoint, plus a `default`.
- `data/clients.csv`: `client_id`, `name`, `discount_pct`.
- `data/prices.csv`: what the pricing service knows: `sku`, `region`, `currency`, `price`.
- `data/requests.csv`: `req_id`, `ts`, `client`, `endpoint`, `sku`, `region`, `currency`.
- `data/invalidations.csv`: `ts`, `sku`, `reason`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Request ids, client ids and endpoints: trim and lower-case. SKUs, regions and
  currencies: trim and upper-case.
- `ts` is `2026-09-20 08:00:00`, `2026-09-20T08:00:00`, or a Unix timestamp in
  **milliseconds** (`1789891200000`). All times are UTC.
- A blank `discount_pct` means 0. Clients not in `clients.csv` get no discount.

### Replay

1. Requests and invalidations are processed together in timestamp order. An invalidation
   with the same timestamp as a request is applied first. Rows with equal timestamps keep
   their file order.
2. An invalidation removes every cached entry for that SKU (any endpoint, region or
   currency).
3. The cache key is the **full** request: `(endpoint, sku, region, currency)`.
4. A cached entry is fresh while its age (request time − time it was stored, in seconds)
   is **less than** the endpoint's TTL. At exactly the TTL it is stale. Endpoints not in
   `ttl.json` use `default`.
5. Fresh entry → `hit`. Otherwise → `miss`: fetch from the pricing service and store the
   result with the request's time. If the service has no price for that
   `(sku, region, currency)`, the outcome is `error`, the price is `None`, and nothing is
   cached.
6. For the `quote` endpoint, the price served is the cached/fetched price
   × (1 − discount_pct ÷ 100), rounded to 2 decimals. `catalog` serves the list price.
   A client's discount applies only to that client's response; it must never change what
   is stored in the cache.

### Report

`quotecache.reports.build_report()` returns:

- `responses`: `req_id` → `{"outcome", "price"}`.
- `summary`:
  - `requests`, `hits`, `misses`, `errors`;
  - `hit_rate`: hits ÷ (hits + misses), rounded to 3 decimals;
  - `origin_calls`: SKU → number of fetches from the pricing service (failed fetches
    count too), sorted by SKU;
  - `span_hours`: hours from the first to the last request in the log, rounded to 2
    decimals;
  - `requests_per_hour`: requests ÷ `span_hours` (unrounded), rounded to 2 decimals.

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
