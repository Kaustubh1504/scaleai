# Box Office Seat Holds

Tickets for a two-day concert go on sale online. A customer first **holds** a seat, then
has a few minutes to **confirm** (pay for) it before the hold lapses. This tool replays
the on-sale event log against the seat map and reports who ended up with which seat.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/seats.csv`: the seat map (`seat_id`, `section`, `price`).
- `data/events.csv`: the on-sale log, one row per customer action (`hold`, `confirm`,
  `release`).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Seat ids and customer ids: trim and upper-case (` c05` → `C05`, `b2` → `B2`), in both
  files. Actions: trim, any case.
- `at` uses `2026-08-14 10:00:00`, `08/14/2026 10:00` (month/day/year) or
  `2026-08-14T10:00:00`.

### Replay

1. Events are applied in time order. Events with the same time are applied in file order.
2. A hold lasts **10 minutes**. A hold placed at time `h` is active at time `t` when
   `t − h` is at most 10 minutes; a confirm exactly 10:00 after the hold is still in time.
   Holds can be older than a day; their age is the full elapsed time.
3. `hold`:
   - unknown seat → rejected `unknown_seat`;
   - seat already sold → rejected `sold`;
   - seat has an active hold by a **different** customer → rejected `seat_held`;
   - otherwise the customer now holds the seat from this event's time (this also
     replaces an expired hold, or restarts the customer's own hold).
4. `confirm`: the customer must have an active hold on that seat (and the seat must not be
   sold); otherwise rejected `no_hold`. On success the seat is sold to the customer and
   the hold ends.
5. `release`: ends the customer's own hold on the seat. Nothing happens otherwise; it is
   never rejected.

### Report

`boxoffice.reports.build_report()` returns:

- `sold`: seat id → customer id, for every sold seat.
- `by_customer`: customer id → sorted list of the seats they bought.
- `rejections`: reason → number of rejected events.
- `revenue`: total price of sold seats, rounded to 2 decimals.
- `occupancy_pct`: sold seats ÷ all seats × 100, rounded to 1 decimal.

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
