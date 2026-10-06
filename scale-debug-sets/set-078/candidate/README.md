# Review Lifecycle Replay

Every labeling task moves through a review lifecycle: an annotator claims and submits
it, a reviewer claims the review and approves or sends it back for rework, and tasks that
keep failing review are escalated to a senior. This tool replays the day's event log
through that state machine, records every event it had to refuse, and reports reviewer
activity, the review queue and cycle times.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/settings.json`: `as_of` (end of the replay), `claim_ttl_minutes`, `max_rework`,
  and `projects` (name → `{"paused": ...}`).
- `data/people.json`: `id`, `role` (`annotator`, `reviewer` or `senior`), `active`.
- `data/tasks.csv`: `task_id`, `project`, `priority`, `created`, and the starting `state`
  (blank means `queued`).
- `data/events.csv`: `ts`, `task_id`, `actor`, `action`. Rows are **not** in time order.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Task ids: trim and upper-case. Person ids, roles, project names, actions and states:
  trim and lower-case.
- Timestamps are `2026-06-10 09:00`, `06/10/2026 09:00` (month/day/year) or
  `2026-06-10T09:00:00`.
- `active` and `paused` are JSON booleans, numbers or strings (`true`, `yes`, `y`, `1`
  mean true). A missing `active` means active; a missing `paused` means not paused.
- Two event rows that are identical **after cleaning** (same time, task, actor and action)
  are one event: keep the first and drop the rest silently.
- Each event is reported by its CSV line number (the header is line 1).

### State machine

| from | action | to |
|---|---|---|
| queued | `claim_label` | labeling |
| labeling | `submit` | submitted |
| submitted | `claim_review` | in_review |
| in_review | `approve` | approved |
| in_review | `reject` | labeling (rework + 1); **escalated** once rework reaches `max_rework` |
| escalated | `resolve` | approved |

Roles: `claim_label`/`submit` need an annotator; `claim_review`/`approve`/`reject` need a
reviewer or senior; `resolve` needs a senior. The actor must exist and be active.

### Replay

Events are applied in timestamp order; equal timestamps keep file order. For each event:

1. Unknown task → violation `unknown task`.
2. If the task is `in_review` and the event time is **after** the claim deadline
   (`claim_review` time + `claim_ttl_minutes`), the claim is released first: the task goes
   back to `submitted` with no claim holder. An event exactly at the deadline is still in
   time.
3. Actor missing, inactive, or in a role that may not perform the action → violation `actor not allowed`.
4. Action not allowed from the current state → violation `invalid transition`.
5. `approve`/`reject` by anyone but the current claim holder → violation `not claim holder`.
6. Otherwise the transition is applied.

A violation leaves the task unchanged. After the last event, step 2 is applied once more
to every task, with `as_of` as the time.

### Report

`revflow.reports.build_report()` returns:

- `states`: task id → final state;
- `rework`: task id → rework count, for tasks with at least one rework;
- `violations`: in replay order, each `{"line", "task", "action", "reason"}`;
- `reviewers`: every **active** reviewer or senior (sorted by id) → `claims` (applied
  `claim_review`s), `approved` (applied `approve`s and `resolve`s) and `rejected`
  (applied `reject`s);
- `review_minutes`: per reviewer, the mean number of minutes between their claim and their
  applied `approve`/`reject` on that claim, rounded to 1 decimal. Each reviewer's mean
  uses only their own decisions, and reviewers with no such decision are left out;
- `queue`: ids of tasks that end in `submitted`, excluding paused projects, ordered by
  priority (**the higher number is more urgent**), then oldest `created`, then task id;
- `cycle_hours`: approved task → hours from `created` to approval, rounded to 2 decimals.

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
