# Vendor Label Feed

Three labeling vendors deliver the same kind of work (sentiment labels on tasks) in
their own export formats. Some tasks were labeled by more than one vendor. This tool
loads every vendor file, validates each row, merges the copies of each task into one
final record, and summarises the result.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/vendors.json`: shared `defaults` plus one entry per vendor (`file`, `priority`,
  optional `label_map`).
- `data/acme.csv`: exported straight from the vendor's spreadsheet tool.
- `data/brightlabel.csv`: same fields as acme, different column order.
- `data/cortex.json`: a list of objects with the same fields. `tags` may be a list or a
  `;`-separated string.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Vendor settings

- Vendor names are trimmed and lower-cased.
- Each vendor's settings start from a copy of `defaults`. Keys in the vendor entry
  replace the default, except `label_map`, which is **merged**: the vendor's own
  entries are added on top of the default map for that vendor only. One vendor's
  settings never change another vendor's.
- **Priority: 1 is the most trusted vendor**; larger numbers are less trusted.

### Cleaning (every vendor)

- Task ids: trim and upper-case. Emails: trim and lower-case.
- Labels: trim and lower-case, then translate through the vendor's `label_map`. A
  label that is not in the map is kept as is.
- `batch`: trim and lower-case. A missing or blank batch is `unbatched`.
- `submitted` uses one of `2026-03-02 09:00`, `2026-03-02T09:00:00`,
  `03/02/2026 09:00` (month/day/year) or `02.03.2026 09:00` (day.month.year).
- `duration_s` is a whole number of seconds. `0` is a real value.
- `tags`: split on `;`, trim and lower-case each one. Blank tags are dropped, and tags
  starting with `tmp:` are internal and are always dropped.

### Validation

A row is rejected, with every reason that applies, in this order:
`missing_task_id` (blank id), `bad_email` (blank or no `@`), `missing_duration`
(blank), `negative_duration` (below 0), `bad_timestamp` (blank or not one of the
formats). Rejected rows are keyed `vendor:N`, where N is the 1-based data row (or list
position) in that vendor's file.

### Merging

1. Accepted rows with the same task id are copies of one task.
2. The winning copy is the one with the latest `submitted`. On equal timestamps, the
   more trusted vendor wins (see priority above).
3. The final record takes `vendor`, `email`, `label`, `batch` and `submitted` from the
   winner. Its `tags` are the sorted, **distinct** tags from all of its copies.

### Report

`vendorfeed.reports.build_report()` returns:

- `rows_read`: vendor → number of rows in its file.
- `rejected`: `vendor:N` → list of reasons.
- `records`: task id → `vendor`, `email`, `label`, `batch`, `submitted`
  (`YYYY-MM-DDTHH:MM`), `tags`.
- `summary`: `label_counts` (final records per label), `tag_counts` (number of final
  records carrying each tag), `by_batch` (final records per batch).

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
