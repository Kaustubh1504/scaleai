# Tenant Metering and Billing

An inference API is shared by many tenants. Each tenant's plan caps how many requests
it may make in a sliding time window, and bills tokens above a free allowance. This
tool replays a day of request logs through the rate limiter, tallies usage, and
produces invoices.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/plans.json`: plan name → `limit` (requests per window), `window_ms` (window
  length in **milliseconds**), `price_per_1k` (USD per 1,000 overage tokens) and
  `included_tokens`.
- `data/tenants.csv`: `tenant_id`, `plan`, `limit_override`.
- `data/requests.csv`: `request_id`, `ts`, `tenant_id`, `endpoint`, `tokens`, `status`
  (the upstream HTTP status).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Tenant ids, plan names, request ids and endpoints: trim and lower-case.
- `ts` is UTC in one of `2026-04-01T10:00:00Z`, `2026-04-01 10:00:00` or
  `04/01/2026 10:00:00` (month/day/year). Requests can span several days.
- Requests from tenants that are not in `tenants.csv` are ignored entirely.

### Limits

1. A tenant's limit is its plan's `limit`, unless `limit_override` is filled in. An
   override replaces the plan limit, and an override of `0` means the tenant is
   suspended: every request is throttled.
2. Requests are processed in timestamp order (equal timestamps keep file order).
3. A request at time `t` is **allowed** if fewer than `limit` of the tenant's
   previously **allowed** requests fall in the window `(t - window, t]`. A request
   exactly one window length earlier is outside the window. Otherwise it is
   **throttled**. Throttled requests do not count toward later windows.

### Usage

4. For each tenant: number of allowed and throttled requests, and allowed requests per
   endpoint.
5. **Billable** requests are allowed requests whose upstream `status` is below 500.
   Client errors (4xx) are still billed; server errors (5xx) are not.
   `billable_tokens` is the sum of their `tokens`.

### Invoices

6. `overage_tokens` = billable tokens above the plan's `included_tokens` (never
   negative).
7. `amount` = overage tokens × `price_per_1k` ÷ 1000, rounded to the cent with halves
   rounded **up** (2.345 → 2.35). Amounts are strings with two decimals.
8. `total` is the sum of all amounts. `top_tenants` are the 3 tenants with the highest
   amount (ties: tenant id ascending).

### Report

`meterbill.reports.build_report()` returns `limits`, `throttled` (sorted request ids
per tenant), `usage`, `invoices`, `total` and `top_tenants`, covering every tenant in
`tenants.csv`.

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
