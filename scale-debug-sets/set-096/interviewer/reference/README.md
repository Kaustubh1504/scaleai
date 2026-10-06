# Holdout Builder

The data team keeps three labelled text datasets (`intent`, `toxicity`, `summaries`) and
re-cuts their train/val/test splits every release. This tool cleans each dataset,
removes duplicate texts, and assigns whole **source documents** to splits so that no
document leaks across splits.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/datasets.json`: shared `defaults` plus per-dataset settings under `datasets`.
  Datasets are processed in the order they appear in that file.
- `data/sources.json`: the source-document registry (`doc`, `license`).
- `data/intent.csv`, `data/toxicity.csv`, `data/summaries.csv`: one row per sample
  (`sample_id`, `doc_id`, `label`, `text`, `quality`, `created`).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Settings

- A dataset's settings are the defaults with that dataset's keys on top. `fractions` is
  merged key by key: a dataset that sets only `test` keeps the default `val`. One
  dataset's settings must never change another dataset's.
- `fractions` are whole percentages for `val` and `test`; `train` gets the rest.
- `pins` maps a document id to the split it must go to. Document ids and split names
  are trimmed and compared case-insensitively.
- `blocked_licenses` compare case-insensitively.

### Cleaning

- Sample ids: trim, upper-case. Document ids: trim, lower-case. Labels: trim,
  lower-case. Text: trim.
- `created` is `2026-01-05`, `01/05/2026` (month/day/year) or `5 Jan 2026`.
- A blank `quality` means the sample is unscored.

Each sample is checked in this order, and the **first** rule it breaks is its drop
reason:

1. `blocked_source`: its document is not in the registry, or the document's license is
   in `blocked_licenses`.
2. `incomplete`: blank text or blank label.
3. `low_quality`: it is scored and `quality < min_quality`. Unscored samples pass.

### Duplicates

4. After cleaning, two samples are duplicates when their texts match ignoring case,
   punctuation and runs of whitespace.
5. In each set of duplicates the **original** is kept: the earliest `created`; on equal
   dates, the lowest sample id. Every other copy is removed and reported as
   `duplicate id → original id`.

### Split assignment (per dataset)

6. Let `n` be the number of samples left. `val = floor(n × val% / 100)`,
   `test = floor(n × test% / 100)`, `train = n − val − test`. These are the **targets**.
7. All samples of one document go to the same split. A document's size is its number of
   remaining samples.
8. Pinned documents go to their pinned split first.
9. The other documents are taken largest first; equal sizes go in document-id order.
   Each one goes to the split with the largest **deficit** (target − samples already
   in that split, which may be negative). If several splits share the largest deficit,
   prefer `train`, then `val`, then `test`.

### Report

`holdout.reports.build_report()` returns, per dataset in file order:

- `kept`: number of samples after cleaning and duplicate removal;
- `dropped`: sample id → drop reason (cleaning rules 1–3 only, sorted by id);
- `duplicates`: duplicate id → original id (sorted by id);
- `targets`: `train`/`val`/`test` targets;
- `groups`: document id → split (sorted by document id);
- `sizes`: samples per split;
- `label_totals`: label → number of kept samples, over the whole dataset.

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
