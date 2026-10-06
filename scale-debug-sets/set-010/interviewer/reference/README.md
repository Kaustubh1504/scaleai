# Tenant Metering and Invoices

Each API tenant is on a plan that sets a request rate limit and a monthly token
allowance. This tool does two jobs for the billing team:

1. **Rate-limit audit**: replays a sample of the gateway's request log through the
   per-tenant limiter and lists which requests were throttled and when the client could
   retry.
2. **Invoices**: totals the metering export for the billing month and prices it.

Invoices are based on the metering export (`usage.csv`) only, not on the request sample.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/config.json`: `billing_period` (`YYYY-MM`), `plans` and `tenants`.
- `data/requests.csv`: `request_id`, `tenant`, `ts_ms` (Unix time in **milliseconds**).
- `data/usage.csv`: `date`, `tenant`, `endpoint`, `tokens` (one row per tenant, endpoint
  and day; `tokens` may contain `,` thousands separators).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Tenant ids, plan names and endpoints: trim and lower-case. Request ids: trim and
  upper-case.
- Dates are `2026-04-02` or `04/02/2026` (month/day/year).

### Rate limiting

1. Requests are replayed in `ts_ms` order (ties: request id).
2. Each plan allows `rpm` requests per sliding 60-second window. A request at time `t`
   is throttled when the tenant already has `rpm` **allowed** requests at times `s` with
   `t - s < 60 000` ms. A request exactly 60 000 ms older no longer counts.
3. Throttled requests are not added to the window.
4. For a throttled request, `retry_after_s` is the number of **seconds** until the oldest
   request in the window leaves it: `(oldest + 60 000 − t) / 1000`.

### Usage

5. Only rows dated inside the billing month count (April 2026: 1 April to 30 April
   inclusive).
6. `monthly_tokens`: tenant → total tokens. `by_endpoint`: tenant → endpoint → total
   tokens.

### Invoices

7. Excess tokens = monthly tokens − the plan's `included_tokens` (never below 0). Excess
   is billed per **started** block of 1 000 tokens at the plan's `overage_per_1k`
   (12 300 excess tokens → 13 blocks).
8. Subtotal = plan `base_fee` + overage.
9. Discount = subtotal × the tenant's `discount_pct` / 100. If a tenant's `discount_pct`
   is blank, missing or `null`, the plan's `default_discount_pct` applies (0 if the plan
   has none). An explicit `0` means no discount.
10. Total = subtotal − discount. Overage, discount and total are rounded to 2 decimals.
11. `top_tenants`: the 3 tenants with the highest total, highest first, as a list of
    tenant ids (ties: tenant id).

### Report

`meterbill.report.build_report()` returns `throttle` (`throttled`: sorted ids,
`retry_after_s`: id → seconds), `usage` (`monthly_tokens`, `by_endpoint`), `invoices`
(per tenant: `plan`, `base`, `overage`, `discount`, `total`) and `top_tenants`.

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
