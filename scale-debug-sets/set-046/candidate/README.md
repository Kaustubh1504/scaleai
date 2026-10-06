# Review Routing Desk

A moderation model labels incoming items and attaches a confidence. Confident
predictions are accepted automatically; the rest are sent to a human review queue and
handed out to reviewers who speak the item's language. The desk also produces a small
calibration report from last week's finished human reviews, and can export everything
as JSON for the dashboard.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/thresholds.csv`: `model_version`, `label`, `min_confidence`. A `label` of `*`
  is the model version's fallback.
- `data/predictions.csv`: one row per model prediction (`item_id`, `model_version`,
  `label`, `confidence`, `priority`, `language`, `received_at`).
- `data/reviewers.json`: the reviewer roster (`id`, `languages`, `capacity`, `active`).
- `data/reviews.csv`: finished human reviews from the previous week.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Item ids and review ids: trim and upper-case (`p-04` → `P-04`). Reviewer ids, model
  versions, labels and languages: trim and lower-case.
- `confidence` is a decimal (`0.62`) or a percentage (`91%`). Any value above 1 is a
  percentage, so `91` and `91%` both mean `0.91`. A blank confidence means the model
  gave none.
- Timestamps use `2026-03-02 09:00`, `03/02/2026 09:00` (month/day/year) or
  `2026-03-02T09:00:00`.
- `languages` is a JSON list or a comma-separated string; blank entries are ignored.
- `capacity` is the number of items a reviewer can take. If it is missing or blank the
  reviewer gets the default of **2**. A capacity of `0` means the reviewer is off rotation
  and takes nothing.
- `active` must be the JSON value `true` to count as active. If it is missing, the
  reviewer is active.

### Predictions

1. If an item id appears more than once, keep only the row with the latest
   `received_at`. On equal timestamps the later row in the file wins.
2. The threshold for a prediction is the `(model_version, label)` row. If there is none,
   use that model version's `*` row. If the model version has no rows at all, use `0.90`.
3. A prediction is **auto**-accepted when its confidence is greater than or equal to its
   threshold. Otherwise it goes to a **human** (reason `low_confidence`). A prediction with
   no confidence always goes to a human (reason `missing_confidence`). Auto rows have
   reason `confident`.

### Review queue

4. `priority` is 1, 2 or 3, and **1 is the most urgent**. The queue is ordered by priority
   (most urgent first), then `received_at` (oldest first), then item id.
5. Walk the queue in order. Each item goes to an active reviewer who speaks its language
   and still has capacity left. Among those, pick the reviewer with the most remaining
   capacity; ties go to the lowest reviewer id. If nobody qualifies the item is
   unassigned.
6. Each human item is due `2`, `8` or `24` hours after `received_at` for priority 1, 2 or
   3.

### Calibration (from `reviews.csv`)

7. Reviews with a blank `human_label` are ignored.
8. `agreement`: for each model label, the share of its reviews where the human label
   equals the model label, rounded to 3 decimals.
9. `reviewer_mix`: for each reviewer, how many reviews they finished with each human
   label.
10. `last_review_at`: the latest `finished_at`.

### Report

`routedesk.reports.build_report()` returns:

- `routing`: item id → `decision` (`auto`/`human`), `reason`, `threshold`;
- `assignments`: every active reviewer id → the item ids they received, in queue order;
- `unassigned`: unassigned item ids in queue order;
- `sla`: human item id → due time (a `datetime`);
- `calibration`: `agreement`, `reviewer_mix`, `last_review_at`.

`routedesk.reports.export_json(report)` returns the report as a JSON string with sorted
keys. Datetimes are written in ISO 8601 form (`2026-03-02T11:05:00`), and sets as sorted
lists.

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
