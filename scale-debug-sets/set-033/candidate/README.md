# NER Span Adjudication

Several annotators marked named entities (people, organisations, locations) in short
news sentences. They used two different tools that export character offsets in
different conventions. This tool normalises every span, keeps the spans that enough
annotators agree on, and reports per-annotator quality.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/documents.json`: `doc_id` and `text` for each sentence.
- `data/annotators.json`: annotator `id` and the `tool` they used (`brat` or `labelkit`).
- `data/spans.csv`: one row per submitted span: `doc_id`, `annotator`, `start`, `end`,
  `label`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Offsets

- Offsets are character indexes into the document text. Internally every span is
  **half-open**: `start` is the first character, `end` is one past the last character,
  so the entity text is `text[start:end]`.
- `brat` exports half-open offsets already. `labelkit` exports `end` as the index of
  the **last** character, so 1 is added to it on load.
- After conversion, leading and trailing whitespace inside the span is trimmed off by
  moving `start` forward and `end` back.

### Cleaning and validity

- Doc ids: trim and upper-case. Annotator ids and tool names: trim and lower-case.
  Labels: trim and upper-case.
- Rows from annotators who are not in `annotators.json` are ignored completely.
- A row is **invalid** if its document is unknown, its label is not one of `PER`, `ORG`,
  `LOC`, or (after conversion) `start < 0`, `end` is past the end of the text, or
  `start >= end`, including after trimming.

### Consensus

1. Two spans are the same when doc, start, end and label all match.
2. A span is **accepted** when at least 2 **distinct** annotators submitted it. An
   annotator who submitted the same span twice counts once.
3. `votes` is the number of distinct annotators behind an accepted span.

### Report

`spanmerge.reports.build_report()` returns:

- `entities`: for every document (including ones with no entities), its accepted spans
  sorted by `(start, end)`, each with `start`, `end`, `label`, `text`, `votes`.
- `annotators`: for every registered annotator with at least one row:
  - `invalid`: number of invalid rows;
  - `agreement`: of the annotator's **distinct** valid spans, the fraction that were
    accepted, rounded to 3 decimals.

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
