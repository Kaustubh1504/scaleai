# Feedback Dataset Splits

Contributors leave free-text feedback, and each comment is labeled `positive`,
`negative` or `neutral`. Before a sentiment model is trained on it, the export has to be
cleaned, deduplicated and split into train, validation and test sets. Comments from the
same source document must stay in the same split so nothing leaks between them.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/items.csv`: one row per comment (`item_id`, `doc_id`, `text`, `label`, `tags`,
  `consent`, `created`).
- `data/config.json`: pinned test documents, excluded tags (both `;`-separated) and the
  validation sample cap.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- `item_id`: trim and upper-case (`i007` → `I007`). `doc_id`: trim and lower-case
  (`DOC-01` → `doc-01`). `label`: trim and lower-case. `text`: trim.
- `tags` is a `;`-separated list, trimmed and lower-cased; blank items are ignored.
- `consent`: blank, `y`, `yes`, `true` or `1` (any case) mean consent was given; any
  other value means it was withdrawn.
- `created` uses one of `2026-01-05`, `01/05/2026` (month/day/year) or `5 Jan 2026`.

### Dropping rows

Apply these in order. A row dropped by one rule is not considered by later rules.

1. **unlabeled**: the label is blank.
2. **excluded**: consent was withdrawn, or any tag is in `exclude_tags`.
3. **duplicate**: two or more remaining rows whose text is the same after lower-casing
   and collapsing runs of whitespace to one space. Keep the one with the earliest
   `created`; if several share the earliest date, keep the lowest `item_id`. The others
   are duplicates.

### Splitting (by document)

4. A document listed in `pinned_test_docs` goes to `test`.
5. Any other document goes by its bucket: `int(md5(doc_id).hexdigest(), 16) % 100`
   (MD5 of the cleaned, UTF-8 doc id). Buckets 0–69 → `train`, 70–84 → `val`,
   85–99 → `test`.
6. Every kept row goes to its document's split.

### Validation sample

7. For each label, take up to `val_cap_per_label` val rows, lowest `item_id` first.

### Report

`splitkit.reports.build_report()` returns:

- `dropped`: `unlabeled`, `excluded` and `duplicate`, each a sorted list of item ids.
- `doc_splits`: doc id → split, for every document with at least one kept row.
- `val_sample`: label → item ids (rule 7).
- `splits`: for each of `train`, `val`, `test`: `size`, `labels` (label → count of rows
  in that split) and `avg_tokens` (mean number of whitespace-separated words per row in
  that split, rounded to 2 decimals).

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
