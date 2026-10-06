# Usage Metering & Invoices

Tenants call our API under a plan. Every call is metered in **units**. This tool replays a
month of request events, applies each tenant's per-minute rate limit (throttled requests
are rejected and never billed), then produces an invoice per tenant and a short
statement for finance.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/plans.json`: plan name → terms: `rpm`, `included_units`, `price_per_1k_cents`,
  `base_cents`.
- `data/tenants.csv`: `tenant_id`, `name`, `plan`, `active`, `rpm_override`.
- `data/credits.json`: tenant id → account credit in cents for this month.
- `data/events.csv`: one row per request: `tenant_id`, `ts`, `endpoint`, `units`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Tenant ids, everywhere (including the keys of `credits.json`): trim and lower-case.
  Plan names: trim and lower-case.
- `active`: `true`, `yes`, `y`, `1` (any case) mean active; blank means active; anything
  else is inactive.
- `rpm_override`: blank means "no override". `0` is a real value (see below).
- `ts` is UTC, written as `2026-05-01T10:00:00Z`, `2026-05-01 10:00:00`, or Unix epoch
  seconds.
- Events for unknown or inactive tenants are ignored everywhere, including the statement.

### Rate limiting

- A tenant's limit is, in order:
  1. its `rpm_override` if set. An override of `0` means the tenant is **suspended**:
     every request is throttled, whatever the plan;
  2. no limit at all for `enterprise` tenants (their plan `rpm` is advisory only);
  3. otherwise the plan's `rpm`.
- Sliding window: process a tenant's events in time order. A request is allowed if fewer
  than `limit` **allowed** requests happened in the 60 seconds before it, where a request
  exactly 60 seconds earlier no longer counts (window `(ts − 60s, ts]`). Throttled
  requests do not use up the window.

### Invoices (one per active tenant)

- `units`: sum of units of **allowed** requests.
- Overage: units above `included_units`, priced at `price_per_1k_cents` per 1,000 units.
  A part-cent always rounds **up** to the next whole cent.
- `gross_cents` = `base_cents` + overage charge.
- `credit_cents`: the credit used, at most `gross_cents`.
- `amount_cents` = `gross_cents` − credit, never below 0.

### Report

`meterbill.reports.build_report()` returns:

- `throttled`: tenant → throttled request times (`YYYY-MM-DD HH:MM:SS`, time order).
- `invoices`: tenant → `plan`, `units`, `gross_cents`, `credit_cents`, `amount_cents`.
- `statement`:
  - `top_tenants`: the 3 tenants with the most requests (allowed **and** throttled), as
    `[tenant, requests]`, most requests first; ties by tenant id A→Z;
  - `plan_mix`: plan → number of active tenants;
  - `total_cents`: sum of `amount_cents`.

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
