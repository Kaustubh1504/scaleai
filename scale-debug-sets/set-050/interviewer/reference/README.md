# Response Rating Panel

Raters score model responses on a 1–10 quality scale. Each response (an **item**) is
rated by several annotators. This tool cleans the submissions, works out a consensus
score per item with a median and a single outlier pass, flags items where raters
disagree for escalation, and summarises the panel.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/annotators.json`: the annotator registry (`id`, `name`).
- `data/items.csv`: `item_id`, `category`, `adjudicated_rating` (an expert's final score,
  usually blank).
- `data/ratings.csv`: one row per submission (`submission_id`, `item_id`,
  `annotator_id`, `rating`, `started_at`, `finished_at`).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Item ids: trim and upper-case. Annotator ids: trim and lower-case. Categories: trim and
  lower-case.
- Ratings are whole numbers from 1 to 10, sometimes written as `6.0`. Blank or out-of-range
  ratings are ignored, as are submissions from annotators not in the registry.
- Timestamps use `2026-05-04 09:00:00`, `05/04/2026 09:00:00` (month/day/year) or
  `2026-05-04T09:00:00`.
- A submission is **rushed** when less than 20 seconds passed between `started_at` and
  `finished_at` in total. Rushed submissions are dropped and counted per annotator.
- If an annotator has more than one remaining submission for the same item, only the one
  with the latest `finished_at` counts (later rows win ties).

### Consensus

1. An item with an `adjudicated_rating` is `adjudicated`: its consensus is that rating
   and its agreement is `None`, whatever the raters said.
2. Otherwise an item with fewer than 3 counted ratings is `insufficient` (consensus and
   agreement `None`).
3. The **median** of a list is the middle value, or the mean of the two middle values
   for an even count (so `6` and `7` give `6.5`).
4. Outlier pass: take the median of the item's ratings. Every rating more than 3 points
   away from it is an outlier and is removed (all of them, in one pass). The consensus is
   the median of the ratings that remain.
5. `agreement` = share of the remaining ratings within 1 point (inclusive) of the
   consensus, rounded to 3 decimals. `agreed` when agreement is at least 0.6, otherwise
   `escalated`.

### Report

`ratingpanel.reports.build_report()` returns:

- `items`: item id → `status`, `consensus`, `agreement`;
- `annotators`: for every registry annotator, `rated` (counted submissions after
  cleaning, before the outlier pass), `rushed`, `outliers`;
- `summary`:
  - `status_counts`: status → number of items;
  - `escalated`: sorted ids of escalated items;
  - `category_means`: category → mean consensus over its items that have one, rounded
    to 2 decimals.

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
