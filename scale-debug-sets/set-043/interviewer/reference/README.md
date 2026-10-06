# Workshop Seat Ledger

Contributors sign up for live training workshops. Signing up is two steps: a **hold**
reserves seats for a short time, and a **confirm** turns the hold into a booking. Staff
can also **comp** seats directly, and anyone can **cancel**. This tool replays the
sign-up event log against the session list and reports each event's outcome plus the
final occupancy.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/sessions.csv`: `session_id`, `title`, `capacity`, `starts_at`.
- `data/events.csv`: `event_id`, `at`, `action` (`hold`, `confirm`, `cancel`, `comp`),
  `session_id`, `attendee`, `seats`. The file is in chronological order.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Session ids: trim and upper-case (` ws-09` → `WS-09`), in both files. Attendees: trim
  and lower-case. Actions: case-insensitive.
- A blank `seats` cell means 1 seat.
- Times use one of `2026-07-08 09:00`, `07/08/2026 09:00` (month/day/year) or
  `2026-07-08T09:00:00`.

### Holds and seats

1. A hold lasts **10 minutes**. It is expired once more than 600 seconds have passed
   since it was placed; a confirm exactly 10 minutes later still succeeds. Expired holds
   don't use up seats.
2. Seats in use for a session = seats of its `confirmed` and `comped` bookings + seats
   of its unexpired holds. A request fits if that plus the requested seats is at most
   the capacity.

### Events (processed in file order)

Every event gets exactly one outcome: `ok` or a rejection reason.

3. Any action on a session id that isn't in `sessions.csv` → `unknown_session`.
4. `hold` and `comp` at or after the session's `starts_at` → `closed`.
5. `hold`: if the attendee already has an unexpired hold or an active booking for the
   session → `duplicate`; else if the seats don't fit → `full`; else `ok` and the hold
   is placed.
6. `confirm`: no hold for the attendee and session → `no_hold`; the hold has expired →
   `expired` (the hold is discarded); else `ok` and a `confirmed` booking with the hold's
   seats is created.
7. `cancel`: an active booking is set to `cancelled` → `ok`; otherwise an unexpired hold
   is released → `ok`; otherwise `nothing_to_cancel`.
8. `comp`: if the seats fit, a `comped` booking is created → `ok`; else `full`.

### Report

`seatbook.report.build_report()` returns:

- `outcomes`: event id → outcome.
- `sessions`: session id → `taken` (seats in `confirmed` + `comped` bookings),
  `capacity`, `fill` (taken ÷ capacity, 2 decimals).
- `full_sessions`: sorted ids of sessions where `taken` equals `capacity`.
- `attendees`: attendee → seats across their `confirmed` and `comped` bookings, for
  attendees with at least one such booking. Cancelled bookings don't count.

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
