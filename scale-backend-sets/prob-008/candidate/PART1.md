# Part 1: Correct earnings from the whole dataset (about 20 minutes)

Finance compared last quarter's payouts with the platform's own numbers and
found people were underpaid. Fix `earnings/` so that it computes the right
amounts from **all** of the data, using the rules below.

In this part, develop against clean data: `make_api(messy=False)` (or
`python -m mock_services.api_server --clean`). Messy data is Part 2.

## Contract (keep these signatures; tests call them)

```python
from earnings.client import EarningsClient, ApiError, AuthError
from earnings.calc import compute_earnings

client = EarningsClient(http, client_id, client_secret, clock)   # http: httpx.Client with base_url set
report = compute_earnings(client, period_start, period_end)      # timezone-aware UTC datetimes
```

* `EarningsClient` must send every request through the given `http` client, so
  tests can point it at the mock. Use `clock` for any time you need.
* Any `/v1` response that is not 2xx raises `ApiError` carrying `.status` and
  `.path`; a non-200 token response raises `AuthError` (a subclass of `ApiError`).
  The existing client already does this. Retrying comes later.

## Fetching

Read **every** annotator, task, submission and review from the top-level list
endpoints (`/v1/annotators`, `/v1/tasks`, `/v1/submissions`, `/v1/reviews`),
following each collection's pagination to the end. Each collection paginates
differently and uses a different envelope; see the table in `API.md`.

## The rules

* **Period.** A submission belongs to the period when
  `period_start <= submitted_at < period_end` (end exclusive, UTC).
* **Verdict.** A submission's verdict is the `verdict` of its **most recent
  review**: the one with the latest `created_at`; if several share the latest
  `created_at`, the one with the highest `id` (ids are fixed-width strings, so
  compare them as strings). A submission with no review is **pending**. A
  review counts no matter when it was made (a review after `period_end` still
  decides the verdict of a submission made in the period).
* **Earnings.** Each **approved** submission earns its task's `reward_cents`.
  Rejected and pending submissions earn nothing. All money is integer cents:
  no floats anywhere in the calculation.

## The report

```json
{
  "period": "2024-04-01T00:00:00Z/2024-04-15T00:00:00Z",
  "annotators": [
    {"annotator_id": "ann_001", "handle": "annotator001",
     "approved": 2, "rejected": 1, "pending": 2, "earnings_cents": 13}
  ],
  "totals": {"annotators": 29, "approved": 82, "rejected": 23, "pending": 78, "earnings_cents": 1253}
}
```

* `period`: `period_label(period_start, period_end)` (already in `calc.py`).
* `annotators`: one row for every annotator with **at least one submission in
  the period**, sorted by `annotator_id`. `handle` comes from the annotator record.
  `approved` + `rejected` + `pending` is the number of the annotator's
  submissions in the period.
* `totals`: `annotators` is the number of rows; the other fields are sums over the rows.
* Extra keys are ignored by finance; you may drop the old ones.

The intern's tests in `tests/` describe the old behaviour; update them. Write
tests against `mock_services.api.make_api()` (see its docstring) that do not depend
on the exact numbers of one seed. `api.insert(...)` lets you add records with
known outcomes.
