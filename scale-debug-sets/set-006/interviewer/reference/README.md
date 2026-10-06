# Review Queue Replay

Labelling tasks move through a review queue: an annotator claims a task, works on it and
submits it, and a reviewer then approves it or sends it back for rework. Every action is
written to an event log. This tool replays the log against the task list and reports the
final state of every task, who did what, and a few queue-health numbers.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/members.json`: everyone who can act on the queue (`id`, `name`, `role`, `active`).
  `role` is `annotator`, `reviewer` or `lead`.
- `data/tasks.csv`: every task (`task_id`, `queue`, `created_at`).
- `data/events.csv`: the event log (`event_id`, `task_id`, `actor`, `action`, `at`). The
  file is **not** in time order.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Task ids and event ids: trim and upper-case. Member ids, roles, queues and actions:
  trim and lower-case.
- A member is active only when `active` is the JSON value `true`, or when `active` is
  missing.
- Timestamps use one of `2026-05-01 08:00`, `05/01/2026 08:00` (month/day/year) or
  `2026-05-01T08:00:00`.

### Replay order

1. Events are applied in timestamp order. Events with the same timestamp are applied in
   event-number order (`E8` before `E12`).

### States and transitions

Every task starts `queued`. The states are `queued`, `claimed`, `submitted`, `approved`
and `escalated`; the last two are terminal.

2. `claim`: the task must be `queued` and the actor must be an annotator. The task becomes
   `claimed` and the actor becomes its assignee.
3. `release`: the task must be `claimed` by this actor. It goes back to `queued` with no
   assignee.
4. `submit`: the task must be `claimed` by this actor. It becomes `submitted`, and the
   actor is recorded as its submitter.
5. `approve`: the task must be `submitted` and the actor must be a reviewer or a lead. The
   task becomes `approved`, and that moment is its close time.
6. `reject`: same conditions as `approve`. The task's rework count goes up by one and its
   assignee is cleared. When the rework count reaches 3 the task becomes `escalated`
   (closed at that moment); otherwise it goes back to `queued`.
7. An event is **invalid**, and changes nothing, when its task id is unknown, its actor is
   unknown or inactive, its action is unknown, or the rule for its action is not met
   (this includes any event on a terminal task).
8. Each task keeps its own history of applied events; `transitions` is its length.

### Report

`reviewflow.reports.build_report()` returns:

- `tasks`: per task id, `state`, `rework`, `assignee` (the current assignee, kept after
  submit and approve; `None` after release or reject) and `transitions`.
- `invalid`: invalid event ids, in the order they were replayed.
- `reviewers`: for each **active reviewer or lead**, how many `approved` and `rejected`
  events they applied.
- `annotators`: for each **active annotator**, `submitted` (submit events applied) and
  `approved` (approved tasks whose submitter they are).
- `summary`:
  - `state_counts`: every state → number of tasks in it;
  - `first_pass_rate`: approved tasks with rework 0 ÷ approved tasks, rounded to 3
    decimals (`None` if nothing is approved);
  - `avg_cycle_hours`: mean of (close time − `created_at`) in hours over approved tasks,
    rounded to 2 decimals (`None` if nothing is approved);
  - `open_by_queue`: queue → number of tasks not in a terminal state.

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
