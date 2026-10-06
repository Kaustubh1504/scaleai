# Span Adjudication

Several annotators mark named entities in short news sentences. Their spans come from two
annotation tools that export offsets differently. This tool converts every span to one
offset convention, cleans it, keeps the spans enough annotators agree on, and resolves
overlaps so each document ends up with one non-overlapping set of entities.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/docs.json`: `doc_id` and `text` for each document.
- `data/spans.csv`: one row per span an annotator marked: `doc_id`, `annotator`, `tool`,
  `start`, `end`, `label`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Offsets

All output offsets are 0-based with an **exclusive** end, so `text[start:end]` is the
entity text.

- `tool = v2`: offsets are already in that form.
- `tool = legacy`: offsets count characters **from 1**, and `end` is the position of the
  entity's **last** character. In `"Flights from Paris"`, legacy marks `Paris` as
  `start=14, end=18`; the output form is `start=13, end=18`.

### Cleaning

- Doc ids: trim, upper-case (`d04 ` → `D04`). Annotator ids: trim, lower-case. Tool
  names: trim, lower-case. Labels: trim, upper-case.
- A span is ignored if its doc is unknown, its offsets are not integers, its label is not
  one of `PER`, `ORG`, `LOC`, `DATE` (a blank label is ignored too), or (after
  conversion) it does not satisfy `0 <= start < end <= len(text)`.
- Leading and trailing whitespace is trimmed from a span by moving its offsets inward. A
  span that is empty after trimming is ignored.

### Agreement

- Two spans agree when they have the same doc, `start`, `end` and `label` after
  conversion and cleaning.
- A span's **votes** is the number of distinct annotators who marked it (an annotator who
  marks the same span twice counts once). A span needs at least **2** votes to be a
  candidate entity.

### Overlaps

Within a document, candidate entities that overlap (share at least one character) are
resolved greedily. Rank candidates by most votes; on equal votes the **longer** span ranks
higher; then the earlier `start`. Walk the ranking and keep each candidate that does not
overlap one already kept.

### Report

`spanmerge.reports.build_report()` returns:

- `documents`: for every doc id (sorted), the kept entities ordered by `start`, each as
  `[start, end, label, text]`.
- `summary`:
  - `entities`: total kept entities;
  - `named_entities`: kept entities labelled `PER` or `ORG`;
  - `docs_without_entities`: doc ids (sorted) with no kept entity;
  - `annotators`: number of distinct annotators among the spans that passed cleaning.

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
