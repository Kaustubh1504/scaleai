# Workshop Seat Holds

Members place **holds** on seats for workshop sessions. A hold only becomes a booking if
the member confirms it within the hold window. Once the holds are settled, each session's
seats are handed out by member tier, and anything that does not fit goes to the waitlist.
This tool settles one day's holds and reports the outcome.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/sessions.csv`: `session_id`, `room`, `capacity`.
- `data/members.csv`: `tier`, `member_id`, `name`. This file is exported from a
  spreadsheet tool and starts with a UTF-8 byte-order mark.
- `data/holds.csv`: `hold_id`, `session_id`, `member_id`, `seats`, `placed_at`,
  `confirmed_at`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Session ids and hold ids: trim and upper-case (` a2 ` → `A2`). Member ids: trim and
  lower-case (`M-02` → `m-02`). Tiers: trim and lower-case.
- A blank `capacity` means the session is closed: capacity `0`.
- A blank `tier` means `standard`.
- Timestamps use one of `2026-09-14 09:00`, `14.09.2026 09:00` (**day.month.year**) or
  `2026-09-14T09:00:00`. A blank `confirmed_at` means the hold was never confirmed.
- Holds with a blank `seats`, an unknown session or an unknown member are ignored
  completely: they are not booked, waitlisted or expired.

### Hold window

1. A hold is **live** when it was confirmed no more than 15 minutes after `placed_at`.
   A confirmation at exactly 15 minutes is still in time.
2. Every other hold (never confirmed, or confirmed too late) is **expired**.

### Allocation (per session, live holds only)

3. Tier priority: `gold` (3) > `silver` (2) > `standard` (1). **The higher number is more
   important.**
4. Holds are processed by tier (most important first), then earliest `placed_at`, then
   `hold_id`.
5. A hold is booked if all its seats fit in what is left of the session's capacity.
   Otherwise it goes to the waitlist, and processing continues with the next hold (a
   smaller hold later in the order may still fit).

### Report

`seatbook.reports.build_report()` returns:

- `sessions`: for every session, `booked` and `waitlist` (sorted hold ids) and
  `seats_booked`.
- `expired`: sorted ids of expired holds.
- `summary`:
  - `seats_left`: capacity − seats booked, for **every** session (sold-out and closed
    sessions show `0`);
  - `total_booked`: seats booked across all sessions;
  - `fill_rate`: `total_booked` ÷ total capacity, rounded to 3 decimals;
  - `top_member`: the member with the most booked seats (ties: lowest member id).

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
