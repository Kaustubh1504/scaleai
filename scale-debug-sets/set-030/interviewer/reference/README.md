# Support Ticket Workflow Replay

The support desk runs every ticket through a configurable workflow: agents triage, start
and reply to tickets, customers answer, and leads sign off on resolutions before the
auto-closer archives them. The allowed moves live in a transition table
(`data/workflow.json`) rather than in code. This tool replays the day's exported event log
against the ticket list, records every event the workflow refused, and reports each
ticket's final state, labels and first-response time, the tickets that missed their
response SLA, and per-person activity.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/tickets.csv`: `ticket_id`, `severity`, `vip`, `opened_at`.
- `data/people.json`: everyone who acts on tickets (`id`, `name`, `role`). `role` is
  `agent`, `lead`, `customer` or `bot`.
- `data/workflow.json`: the transition table. Each entry has `from`, `action`, `to`,
  `roles` (who may take it) and optionally `counts_as_response`.
- `data/events.csv`: `seq`, `ts`, `ticket_id`, `actor`, `action`, `value`. The export is
  **not** in time order.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Ticket ids: trim and upper-case. Person ids (in people.json and event actors), roles,
  states, actions and tag values: trim and lower-case, so `Noor` and `noor` are the same
  person.
- Flags (`vip`, `counts_as_response`) may be real JSON booleans or text. Text is true only
  for `true`, `yes`, `y` or `1` (any case, surrounding spaces ignored); anything else,
  including a blank cell, `"no"` and `"false"`, is false. A missing `counts_as_response`
  is false.
- Times use `2026-05-04 09:00`, `2026-05-04T09:00:00` or `05/04/2026 09:00`
  (month/day/year).
- `severity` is an integer and **1 is the most urgent** (3 is the least).

### Replay

- Events are applied in timestamp order; events with the same timestamp are applied in
  `seq` order.
- Every ticket starts in state `new` at its `opened_at`, with no labels.
- A workflow action is accepted when the transition table has an entry whose `from` is
  the ticket's current state, whose `action` matches, and whose `roles` include the
  actor's role. The table may hold **several entries for the same state and action** with
  different roles and targets (an agent's resolve waits for approval, a lead's resolve is
  final); the first entry, in file order, that the actor's role may take is used.
- An accepted action moves the ticket to the entry's `to` state and sets `updated_at` to
  the event time. If the entry `counts_as_response` and the ticket has no first response
  yet, the event time becomes the ticket's first response. Later responses never replace
  it.
- `tag` is not in the table. Anyone may tag a ticket that is not `closed`; the value is
  added to the ticket's labels once (duplicates are ignored), in the order first added.
  Tagging does not change the state or `updated_at`.
- An actor who is not in people.json has no role.

### Refused events

A refused event changes nothing and is recorded as `[HH:MM, ticket_id, actor, action,
reason]`, in replay order. The reason is the first that applies:

1. `unknown_ticket`: the ticket id isn't in tickets.csv.
2. `invalid_transition`: no entry exists for the ticket's state and the action (or a tag
   on a closed ticket).
3. `role_not_allowed`: entries exist for that state and action, but none lists the
   actor's role.

### Response SLA

| severity | minutes to first response |
|---|---|
| 1 | 30 |
| 2 | 120 |
| 3 | 480 |

VIP tickets get half the time. A ticket **breaches** when the minutes from `opened_at` to
its first response, or to `as_of` if it has none, are **more than** its limit. Responding
exactly at the limit is on time.

### Report

`ticketflow.reports.build_report()` returns:

- `as_of`: the end of the replay, `2026-05-04 18:00`, as a datetime.
- `tickets`: per ticket id (sorted), `state`, `labels`, `first_response_min` (minutes from
  `opened_at` to the first response, rounded to 1 decimal, or `None`) and `updated_at`
  (datetime of the last accepted workflow action, or `None`).
- `rejected`: the refused events, as above.
- `sla_breaches`: sorted ids of breaching tickets.
- `actors`: for every actor in events.csv (sorted), the number of events per action
  (sorted), counting every row in the log, accepted or not.

`ticketflow.reports.to_json(report)` serialises the report, with datetimes in ISO format.

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
