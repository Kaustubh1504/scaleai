# Label Consensus

Several annotators label each image task. A few tasks are **gold** tasks with a known
answer, and they are used to measure each annotator. This tool scores annotators on the
gold tasks and then works out a weighted-vote consensus label for every other task.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/annotators.json`: the annotator registry (`id`, `name`, `active`).
- `data/tasks.csv`: every task. `gold_label` is filled in for gold tasks only.
- `data/annotations.csv`: one row per submitted label.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Task ids: trim and upper-case (`t04` → `T04`). Annotator ids: trim and lower-case
  (` ANN-05` → `ann-05`). Labels: trim and lower-case.
- `active` may be a JSON boolean, a number (`0`/`1`), or a string. As a string,
  `true`, `yes`, `y` and `1` (any case) mean active and anything else means inactive.
  If `active` is missing, the annotator is active.
- `submitted_at` uses one of `2026-03-02 09:00`, `03/02/2026 09:00` (month/day/year)
  or `2026-03-02T09:00:00`.
- Annotation rows with a blank label are ignored.

### Which annotations count

1. Ignore annotations from annotators who are not in the registry, or who are inactive.
2. If an annotator submitted more than once for the same task, keep only the submission
   with the latest `submitted_at`. If two share the same timestamp, the one that comes
   later in the file wins.

### Annotator quality

3. An annotator's **accuracy** is the number of gold tasks they answered correctly,
   divided by the number of gold tasks they answered.
4. An annotator who answered no gold tasks gets a prior accuracy of `0.5`.
5. An annotator is **blocked** when their accuracy is below `0.5`. Exactly `0.5` is not
   blocked.

### Consensus (non-gold tasks only)

6. Only votes from annotators who are not blocked count. Each vote weighs the voter's
   accuracy.
7. A task with fewer than 2 counting votes has status `needs_more_votes` (label and
   confidence `None`).
8. Otherwise the label with the highest total weight wins and the status is `resolved`.
   On a tie in total weight, the alphabetically first label wins.
9. `confidence` = winning label's weight ÷ total weight of all counting votes on the
   task, rounded to 3 decimals.

### Report

`consensus.reports.build_report()` returns:

- `annotators`: for each **active** registry annotator, `accuracy` (rounded to 3
  decimals), `gold_answered` and `blocked`.
- `consensus`: for each non-gold task, `status`, `label`, `confidence`, `votes`
  (the number of counting votes).
- `summary`:
  - `label_counts`: winning label → number of **resolved** tasks with that label;
  - `needs_more_votes`: sorted task ids with that status;
  - `most_disputed`: the resolved task with the lowest confidence (ties: lowest task id).

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
