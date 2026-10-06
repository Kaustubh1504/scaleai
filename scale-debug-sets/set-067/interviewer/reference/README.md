# Seat Holds

A small box-office engine for a single show. Customers place temporary **holds** on
seats, then confirm (buy) or release them. Holds that are not confirmed in time expire
and the seats go back on sale. The tool replays a day's request log against the seat map
and reports the seats granted, the outcome of every request, and the sales.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/seats.csv`: the seat map (`section`, `row`, `number`, `tier`).
- `data/requests.csv`: the request log (`request_id`, `ts`, `action`, `customer`,
  `section`, `quantity`). Rows are not necessarily in time order.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Sections, rows and request ids: trim and upper-case. Customers, actions and tiers: trim
  and lower-case. Seat numbers are integers (stray spaces allowed).
- `ts` uses one of `2026-05-01 09:00`, `05/01/2026 09:00` (month/day/year) or
  `2026-05-01T09:00:00`.
- A blank `quantity` means 1.

### Processing

Requests are processed in `ts` order; requests with the same `ts` keep their file order.
Before each request is handled, **expiry** runs: every active hold whose age (request
`ts` − hold time) is **15 minutes or more** expires, and its seats become available again.
Ages are measured in real elapsed time, so a hold from the previous day is long expired.

Each customer has at most one active hold. By action:

- `hold`: if the customer already has an active hold → `duplicate`. Otherwise pick the
  best available seats in the requested section: sort the available seats by row, then
  by seat **number** (numerically: 2 comes before 10), and take the first `quantity`.
  If fewer than `quantity` seats are available → `rejected` (no partial holds).
  Otherwise the seats become held → `held`.
- `confirm`: the customer's active hold becomes sold → `confirmed`. No active hold
  (never held, already expired or released) → `no_hold`.
- `release` or `cancel`: the customer's active hold is freed → `released`. No active
  hold → `noop`.
- Any other action → `ignored` (nothing changes).

### Report

`seatbook.reports.build_report()` returns:

- `held_seats`: request id → seat labels (`ORCH-A9`) granted by each successful hold,
  in the order they were picked;
- `statuses`: request id → outcome; `actions`: request id → cleaned action;
- `summary`:
  - `sold`: number of sold seats at the end of the log;
  - `revenue`: sum of sold seat prices: `premium` 120, `standard` 80, `balcony` 55;
  - `sold_by_section`: section → sold seats;
  - `ignored`: sorted ids of requests with outcome `ignored`.

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
