# Review Router

A labelling pipeline runs a model over incoming items. Confident predictions are
accepted automatically; everything else goes to a human review queue. This tool routes
each prediction, assigns review items to reviewers with the right skills, orders each
reviewer's worklist by urgency, and summarises the run.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/predictions.csv`: one model prediction per row (`item_id`, `task`, `label`,
  `confidence`, `sensitive`, `priority`, `created_at`).
- `data/policies.json`: per task, the confidence `threshold`, the default `priority` and
  `always_review` labels.
- `data/reviewers.json`: reviewers (`id`, `skills`, `active`, `capacity`).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Item ids: trim and upper-case. Tasks, labels, reviewer ids and skills: trim and
  lower-case (in every file).
- `confidence` is a decimal (`0.62`) or a percentage (`91%`). Blank means the model gave
  no confidence. `0` is a real confidence of zero.
- `sensitive` is a flag: `yes`, `y`, `true` or `1` (any case, stray spaces) mean
  sensitive. Anything else, including `no`, `false`, `N` and blank, means not sensitive.
- **Priority: 1 is the most urgent**; larger numbers are less urgent. A blank `priority`
  takes the task's default from `policies.json`.
- `created_at` uses one of `2026-06-10 08:00`, `06/10/2026 08:00` (month/day/year) or
  `2026-06-10T08:00:00`.
- A reviewer with no `active` key is active.

### Routing

Checks run in this order; the first match decides:

1. sensitive → `human_review`, reason `sensitive`;
2. label in the task's `always_review` list → `human_review`, `label_policy`;
3. no confidence → `human_review`, `no_confidence`;
4. confidence **below** the task threshold → `human_review`, `low_confidence`
   (exactly the threshold is accepted);
5. otherwise → `auto_accept`, reason `confident`.

### Assignment

- Review items are assigned in item id order. Each goes to the eligible reviewer (active,
  has the task as a skill, fewer assigned items than `capacity`) with the fewest items
  assigned so far; ties go to the lowest reviewer id. Load counts across all tasks.
- An item no eligible reviewer can take goes to the backlog (unassigned).

### Worklists

Each reviewer's items are ordered most urgent first:

1. lower `priority` number first;
2. then lower confidence first (no confidence comes before any number);
3. then older `created_at` first.

### Report

`hitlroute.reports.build_report()` returns:

- `routing`: item id → `task`, `decision`, `reason`;
- `assignments`: review item id → reviewer id (or `None` if in the backlog);
- `backlog`: backlog item ids in assignment order;
- `worklists`: reviewer id → ordered item ids (reviewers with at least one item);
- `summary`:
  - `auto_accept_rate`: task → auto-accepted ÷ all items of that task, rounded to 3 decimals;
  - `review_load`: reviewer → assigned items; `backlog`: number of backlog items;
  - `mean_review_confidence`: mean confidence of the **review** items that have a
    confidence, rounded to 3 decimals.

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
