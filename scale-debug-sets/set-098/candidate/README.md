# Quorum

Three moderation queues (`tox`, `spam`, `quality`) are labelled by a mixed pool of
experts, standard annotators and trainees, through two vendors that export votes in
different formats. This tool screens the votes, keeps each annotator's latest answer,
and works out a tier-weighted consensus per item, plus a per-queue quality report.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/annotators.json`: `id`, `tier` (`expert`/`standard`/`trainee`), `active`,
  `queues` (`;`-separated queue names; blank means **every** queue).
- `data/queues.json`: tier `weights`, per-queue `labels`, `threshold` and `min_votes`,
  and label `aliases`.
- `data/items.csv`: `item_id`, `queue`, `min_votes` (blank → the queue's value),
  `closes_at` (blank → no deadline).
- `data/vendor_a.csv`: `vote_id`, `item_id`, `annotator`, `label`, `submitted_at`. Times
  are UTC: `2026-03-02 09:00`, `2026-03-02T09:00:00Z` or `03/02/2026 09:00`
  (month/day/year).
- `data/vendor_b.jsonl`: one JSON object per line: `id`, `task` (item id), `worker`
  (annotator id), `answer` (label), `submitted` (**Unix time in seconds**, UTC).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Normalisation

- Item ids: trim, upper-case. Annotator ids, queue names, tiers and labels: trim,
  lower-case. Then map a label through `aliases` if it has an entry.
- `active` is a JSON boolean, a number, or a string (`true`, `yes`, `y`, `1` in any case
  mean active).

### Screening (each vendor separately)

A vote is rejected for the first of these that applies:

1. `unknown_item`: the item is not in `items.csv`.
2. `unknown_annotator`: the annotator is not in the registry.
3. `inactive`: the annotator is inactive.
4. `not_certified`: the annotator lists queues and the item's queue is not one of them.
5. `invalid_label`: the label (after aliasing) is blank or not one of the queue's labels.

### Latest answer

6. Across both vendors, keep only each annotator's latest vote per item. If two share a
   time, the later one in the combined list (vendor A rows first, then vendor B) wins.
   Every other vote is **superseded**.

### Consensus (per item)

7. Votes submitted after the item's `closes_at` do not count. A vote exactly at
   `closes_at` counts.
8. Fewer counting votes than `min_votes` → `pending` (label and agreement `None`).
9. Each vote weighs its annotator's tier weight. The label with the highest total wins.
   On a tie, the label with more **expert** votes wins; then the alphabetically first.
10. `agreement` = winning weight ÷ total weight, rounded to 3 decimals.
    `accepted` if agreement ≥ the queue's `threshold`, otherwise `escalated` (the
    leading label is still reported).
11. An item has **expert dissent** if any counting expert vote is for a different label
    than the winner.

### Report

`quorum.reports.build_report()` returns:

- `rejected`: per vendor, vote id → reason, for that vendor's votes only;
- `superseded`: sorted ids of superseded votes;
- `queues`: per queue (sorted by name):
  - `items`: item id → `status`, `label`, `agreement`, `votes` (counting votes);
  - `status_counts`: number of items per status;
  - `agreement`: for each annotator with at least one counting vote on an
    **accepted** item of the queue, the share of those votes that match the label,
    rounded to 3 decimals;
  - `contested`: sorted ids of **accepted** items whose agreement is below 0.8 or that
    have expert dissent.

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
