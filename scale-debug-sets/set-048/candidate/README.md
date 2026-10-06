# Grouped Dataset Splitter

Builds train / val / test splits for an image-classification dataset. Samples come in
**groups** (all crops from the same source photo share a group), and a group must never
be split across train and evaluation, otherwise the model is scored on near-copies of its
training data. Splits are stratified by each group's majority label, and the train split
is capped per label so one class doesn't dominate.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/samples.csv`: `sample_id`, `group_id`, `label`, `created_at`, `exclude`.
- `data/config.json`: `val_percent`, `test_percent`, `train_cap_per_label`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Sample ids: trim and upper-case (` s-019` → `S-019`). Group ids and labels: trim and
  lower-case (`G-13` → `g-13`).
- `created_at` uses `2026-01-05 08:00`, `01/05/2026 08:00` (month/day/year), or a bare
  date in either style (midnight).
- Rows are processed in file order:
  1. A row with a blank label is ignored completely.
  2. `exclude` marks a row to leave out. `y`, `yes`, `true` and `1` (any case) mean
     excluded; blank, `no`, `false` or anything else means keep. Excluded rows are listed
     in `excluded`.
  3. A non-excluded row whose sample id was already kept is a duplicate: it is dropped and
     its id listed in `duplicates`. The first kept row wins.

### Group labels and strata

4. A group's label is the most frequent label among its kept samples. On a tie, the
   alphabetically first label wins.
5. Groups are stratified by group label. Within a stratum, order the groups by group id.
   With `n` groups, `n_test = n × test_percent // 100` and `n_val = n × val_percent // 100`
   (both rounded down). The first `n_test` groups go to **test**, the next `n_val` to
   **val**, and all remaining groups to **train**. Every group gets exactly one split.
6. Every kept sample goes to its group's split.

### Train cap

7. In **train** only, keep at most `train_cap_per_label` samples of each sample label:
   the earliest `created_at` first (ties: lower sample id). The rest are listed in
   `capped`. Val and test are never capped.

### Report

`splitkit.reports.build_report()` returns:

- `excluded`, `duplicates`, `capped`: sorted sample ids;
- `group_labels`: group id → label; `group_split`: group id → split;
- `splits`: `train`/`val`/`test` → sorted sample ids (after the cap);
- `label_counts`: split → {label: number of samples in that split}, listing every label
  that appears in any kept sample (zero when absent from the split).

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
