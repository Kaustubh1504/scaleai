# Two-Level Review Flow

Every labelled task goes through two independent reviews before it is accepted. A level-1
reviewer claims the task and either passes it, sends it back for changes, or rejects it.
A passed task then waits for a **different** level-2 reviewer, who makes the final call.
This tool replays the review event log against the task list and reports where every
task ended up.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/tasks.csv`: `task_id`, `author`, `project`, `priority`, `submitted_at`.
- `data/events.csv`: `at`, `task`, `actor`, `action`, already in time order.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Task ids: trim and upper-case. People (authors and actors): trim and lower-case, so
  `Dana` and `dana` are the same reviewer. Actions: trim and lower-case.
- `priority` is an integer and **a higher number is more important** (3 beats 1).
- Times use `2026-07-06 09:00`, `07/06/2026 09:00` (month/day/year) or `2026-07-06T09:00`.

### States and actions

States: `submitted`, `l1_review`, `awaiting_l2`, `l2_review`, `changes_requested`,
`approved`, `rejected`. Every task starts in `submitted` at its `submitted_at`.

| action | allowed from | by | result |
|---|---|---|---|
| `claim` | `submitted` | anyone but the author | `l1_review`, actor is the level-1 reviewer |
| `claim` | `awaiting_l2` | anyone but the author and the level-1 reviewer | `l2_review`, actor is the level-2 reviewer |
| `pass` | `l1_review` / `l2_review` | the reviewer holding that level | `awaiting_l2` / `approved` |
| `request_changes` | `l1_review` / `l2_review` | the reviewer holding that level | `changes_requested` |
| `reject` | `l1_review` / `l2_review` | the reviewer holding that level | `rejected` |
| `resubmit` | `changes_requested` | the author | `submitted`; revision + 1; both reviewers cleared |

`approved` and `rejected` are final (**decided**).

### Refused events

An event that breaks the table changes nothing and is recorded with a reason, checked in
this order:

1. `unknown_task`: the task id isn't in tasks.csv.
2. `invalid_transition`: the action doesn't exist, or isn't allowed from the task's
   current state.
3. `conflict_of_interest`: a claim by the task's author, or a level-2 claim by the
   task's level-1 reviewer.
4. `not_assignee`: anyone else acting who isn't allowed to (not the reviewer holding the
   task, or not the author for `resubmit`).

### Report

`reviewflow.reports.build_report()` returns:

- `states`, `revisions`: per task.
- `rejected`: `[time, task, actor, action, reason]` for every refused event, in order.
- `history`: per task, the list of states it has been in, starting with `submitted`.
- `queue`: tasks waiting for a reviewer (`submitted` or `awaiting_l2`) as
  `[task, state]`: highest priority first, then the task that has been waiting in its
  current state the longest, then task id.
- `reviewers`: for every person with at least one accepted claim, the number of accepted
  `pass` (`passed`), `request_changes` (`changes`) and `reject` (`rejected`) actions.
- `cycle_hours`: for decided tasks, hours from `submitted_at` to the decision, rounded to
  1 decimal.
- `summary`: `by_state` (final state → number of tasks) and `approval_rate` = approved ÷
  decided, rounded to 3 decimals.

Times are formatted `YYYY-MM-DD HH:MM`.

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
