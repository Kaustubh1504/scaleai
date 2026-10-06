# Moderation Review Router

Three moderation models label incoming content. This tool decides, for each prediction,
whether it can be auto-accepted or needs a human: an expert reviewer for serious labels,
or the crowd queue for minor ones. It then hands the expert items to reviewers in each
language pool, and builds a calibration report from yesterday's human reviews.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/policy.json`: `default_threshold`, `legacy_models`, and one rule per label:
  `label`, `severity`, `threshold` (may be `null`), `sensitive` (optional, default false).
- `data/predictions.csv`: `item_id`, `model`, `label`, `confidence`, `received_at`,
  `lang`, `flagged`.
- `data/reviewers.csv`: `reviewer_id`, `name`, `pool`, `active`, `capacity`, `senior`.
- `data/reviews.csv`: yesterday's human reviews: `item_id`, `model`, `model_label`,
  `confidence`, `human_label`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Item ids: trim and upper-case. Model names, labels, languages, pools and reviewer ids:
  trim and lower-case. A blank `lang` means `en`.
- `confidence` is a decimal (`0.91`, or `0,91` with a decimal comma) or a percentage
  (`91%`). Blank means no confidence.
- `flagged`, `active` and `senior` are true for `yes`, `y`, `true` or `1` (any case), and
  false for anything else, including blank.
- `received_at` is `2026-09-28 09:00`, `28/09/2026 09:00` (**day/month/year**) or
  `2026-09-28T09:00:00`.

### Severity

Severity runs from 1 to 5, and **5 is the most severe**. Labels with no rule in the policy
are treated as severity 3.

### Routing (first matching rule wins)

1. Label not in the policy → `expert`, reason `unknown_label`.
2. Sensitive label → `expert`, reason `sensitive`.
3. Flagged → the fallback route (below), reason `flagged`.
4. No confidence → the fallback route, reason `no_confidence`.
5. Confidence ≥ the label's threshold → `auto`, reason `confident`. A `null` threshold
   means `default_threshold`. A threshold of `0.0` is a real threshold: every prediction
   with a confidence passes it.
6. Otherwise → the fallback route, reason `low_confidence`.
7. Models listed in `legacy_models` may never auto-accept. A prediction that would be
   `auto` under rule 5 goes to `crowd` instead, reason `legacy_model`.

The **fallback route** is `expert` for severity 3 and above, and `crowd` for severity 1–2.

### Expert assignment

8. Expert items are split into pools by `lang`. A reviewer belongs to the pool named in
   their `pool` column.
9. Within a pool, items are handled most severe first, then earliest `received_at`, then
   `item_id`.
10. A reviewer can take an item if they are active, have fewer items than their
    `capacity`, and (for severity-5 items only) are senior.
11. The item goes to the reviewer who can take it and has the fewest items so far (ties:
    lowest reviewer id). If nobody can take it, it goes to that pool's backlog.

### Calibration (from `reviews.csv`; rows with a blank confidence are ignored)

12. Per model: `reviews`, `agreement` (share of reviews where `model_label` equals
    `human_label`), `mean_confidence`, and `gap` = mean_confidence − agreement. All
    rounded to 3 decimals, and `gap` is computed from the unrounded values.
13. Per `model_label`: the `human_label` most often given when the human disagreed. Ties
    go to the alphabetically first label. A label with no disagreements gets `None`.

### Report

`hitlroute.reports.build_report()` returns `decisions` (item → `route`, `reason`),
`assignments` (every reviewer → items in the order assigned), `backlog` (pool → item ids
in handling order, for pools that had expert items) and `calibration` (`models`,
`confusions`).

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
