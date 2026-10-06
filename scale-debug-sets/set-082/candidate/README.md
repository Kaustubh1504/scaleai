# Gateway Metering

Every API call that passes through the gateway is logged with the tenant and the
number of units it consumed. This tool replays the log through each tenant's rate
limiter, then turns the accepted traffic into monthly invoices with tiered pricing,
discounts and account credits.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/plans.json`: plan name → rate limit, whether it is billed, monthly fee, included
  units and price tiers.
- `data/tenants.csv`: `tenant_id`, `plan`, `rate_override`, `discount_pct`.
- `data/requests.csv`: the gateway log: `request_id`, `tenant_id`, `ts`, `endpoint`, `units`.
- `data/credits.json`: account credits: `credit_id`, `tenant_id`, `month`, `amount` (dollars).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.
All money is handled in integer cents.

### Cleaning

- Tenant ids and plan names: trim and lower-case. Request ids: trim.
- `ts` is one of `2026-03-02T09:00:00Z`, `2026-03-02T09:00:00+01:00` (any UTC offset),
  `2026-03-02 09:00:00` or `03/02/2026 09:00:00` (month/day/year). Timestamps without an
  offset are UTC, and seconds may carry a fraction (`08:00:01.750Z`). Everything is
  converted to UTC, and the **UTC** calendar month decides the billing month.
- `units` must be a whole number (surrounding whitespace is fine).
- A log row whose tenant is not in `tenants.csv` is skipped as `unknown_tenant`. Otherwise,
  a row whose `units` or `ts` cannot be parsed is skipped as `malformed`. Skipped rows
  take no further part: they are not rate limited and not billed.
- `discount_pct` may be blank (0), a number, or a number with `%`.
- Credit `month` is `2026-03` or `03/2026`; `amount` is a number or numeric string in
  dollars.

### Rate limiting

- A tenant's limit is `rate_override` when it is set (`N/Ws` = N requests per W seconds,
  `N/Wm` = per W minutes), otherwise the plan's `limit` per `window_s` seconds.
- Each tenant's requests are replayed in timestamp order. Requests with the **same**
  timestamp keep their order in the log.
- Sliding window: a request at time `t` is accepted when the tenant has fewer than `N`
  accepted requests with a timestamp in the half-open interval `(t − W, t]`. A request
  exactly `W` seconds after an earlier one no longer counts that earlier one.
  Rejected requests do not count towards later decisions.
- A rejected request gets a retry hint: the seconds until the oldest accepted request in
  its window leaves the window, i.e. `W − (t − oldest)`, rounded to 3 decimals.

### Invoices

- Only plans with `billed: true` get invoices. A tenant gets one invoice per month in
  which it has at least one accepted request.
- `usage_units`: total units of the month's accepted requests.
- Billable units are `usage_units − included_units` (never below 0), billed in blocks of
  1,000 units. A partial block counts as a whole block.
- Tiers are graduated: blocks up to the first tier's `up_to_blocks` are priced at that
  tier's rate, the next blocks up to the next limit at the next rate, and so on; `null`
  means no upper limit.
- `subtotal_cents` = monthly fee + tiered block cost.
- `total_cents` = subtotal reduced by `discount_pct` percent, rounded to the nearest cent;
  an exact half cent rounds **up**.
- Credits are applied in file order to the invoice for their tenant and month. Each one
  reduces what is still owed, but never below zero: a credit larger than the remaining
  amount is only partly used. A credit with no matching invoice is listed in
  `unapplied_credits` (in file order).
- `due_cents` = `total_cents − credits_cents`.

### Report

`meterbill.reports.build_report()` returns `skipped` (sorted ids per reason),
`tenants`, `limits` (tenant → `[N, window_seconds]`), `timeline` (tenant → request ids in
replay order), `rejected` (request id → retry hint), `invoices` (keyed `tenant/YYYY-MM`)
and `unapplied_credits`.

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
