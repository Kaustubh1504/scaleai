# Human-in-the-loop Triage

A content-labeling model scores every item it sees. Confident predictions are accepted
automatically; everything else goes to a human review queue, and the queue is handed out
to reviewers who speak the item's language. This repo runs one triage pass over an
exported batch and reports the result.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/predictions.csv`: one row per model prediction. A prediction may be re-scored,
  in which case the same `pred_id` appears more than once.
- `data/thresholds.json`: the default confidence threshold, per-task-type overrides, and
  the `;`-separated flags that always need a human.
- `data/reviewers.csv`: the reviewer roster.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- `pred_id` and `reviewer_id`: trim and upper-case. `task_type`, `lang`, flags and
  reviewer languages: trim and lower-case, in the CSVs and in `thresholds.json`.
- `flags` and `languages` are `;`-separated lists; blank items are ignored.
- A blank `confidence` means the model gave **no score**. A blank `priority` means `0`.
- `created_at` uses one of `2026-04-01 10:00`, `2026/04/01 10:00` or
  `01.04.2026 10:00` (day.month.year).
- `active`: blank, `y`, `yes`, `true` or `1` (any case) mean active; anything else
  means inactive.

### Re-scored predictions

1. Keep exactly one row per `pred_id`: the one with the latest `created_at`. On equal
   `created_at`, the row later in the file wins. Every later step works on these rows,
   sorted by `pred_id`.

### Routing

2. The threshold for a prediction is its task type's override, or `default` if the task
   type has none. A threshold of `0` is a real threshold (everything scored passes).
3. Check in this order:
   - any flag listed in `always_human_flags` → `human`, reason `flagged`;
   - no score → `human`, reason `no_score`;
   - `confidence >= threshold` → `auto`, reason `confident`;
   - otherwise → `human`, reason `low_confidence`.

### Review queue

4. The queue holds every `human` prediction. **Higher priority numbers are more urgent**
   and come first. Within a priority, the lower confidence comes first, with no-score
   items before any scored item. Remaining ties: `pred_id` ascending.

### Assignment

5. Only active reviewers take work. Go through the queue in order. A reviewer can take
   an item if they list its `lang` and still have spare capacity (each item uses one
   unit of `capacity`).
6. Of the reviewers who can take it, the item goes to the one with the most remaining
   capacity; ties go to the lowest reviewer id. If nobody can take it, the item goes to
   the backlog.

### Report

`triage.reports.build_report()` returns:

- `decisions`: one per kept prediction, sorted by `pred_id`: `pred_id`, `route`
  (`auto`/`human`) and `reason`.
- `queue`: pred ids in queue order.
- `assignments`: active reviewer id → pred ids in the order they were assigned
  (every active reviewer appears, even with no work).
- `backlog`: pred ids that nobody could take, in queue order.
- `summary`:
  - `by_task_type`: task type → `auto`, `human` and `human_rate` (human ÷ total for that
    type, rounded to 3 decimals);
  - `busiest_reviewer`: the reviewer with the most assigned items (ties: lowest id);
  - `backlog_size`.

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
