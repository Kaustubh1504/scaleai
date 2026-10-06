# Entity Span Audit

Annotators mark named entities in short news snippets by selecting character ranges.
Their selections are sloppy: stray spaces, half-selected words, label aliases. This tool
cleans every selection into a canonical span, exports the spans for documents that have
no adjudicated answer yet, and scores each annotator against the adjudicated (gold) spans.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/documents.json`: `doc_id` and `text` for every document.
- `data/labels.json`: label aliases. Each row maps an `alias` to a canonical `label`.
- `data/annotations.csv`: one row per selection: `doc_id`, `annotator`, `start`, `end`, `label`.
- `data/gold.csv`: adjudicated spans: `doc_id`, `start`, `end`, `label`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Conventions

- Offsets are character offsets into `text`, **end-exclusive**: the span covers
  `text[start:end]`.
- Doc ids: trim and upper-case (`d04` → `D04`). Annotator ids: trim and lower-case.
  Offsets may have surrounding whitespace.
- Canonical labels are upper-case. A label is resolved by trimming and lower-casing it
  and looking it up among the aliases **and** the canonical labels themselves
  (`Person ` → `PERSON`, `gpe` → `LOC`). A blank alias registers nothing.
- Gold labels are already canonical, in any case (`loc` → `LOC`).

### Cleaning a selection

Checks run in this order; the first one that fails rejects the row with that reason:

1. `unknown_doc`: the doc id is not in `documents.json`.
2. `unknown_label`: the label does not resolve.
3. `missing_offset`: `start` or `end` is blank.
4. `out_of_range`: unless `0 <= start < end <= len(text)`.
5. `empty`: after trimming whitespace off both ends of the selection, nothing is left.

A selection that passes is trimmed (step 5), then **snapped to tokens**. Tokens are
words (letters/digits/underscore, keeping inner apostrophes such as `O'Brien`) and single
punctuation marks. Every token that shares at least one character with the trimmed
selection is covered, and the span is widened to run from the first covered token's
start to the last covered token's end. A selection of `Watanab` becomes `Watanabe`.

After cleaning, a span identical to an earlier accepted one (same doc, annotator, start,
end and label) is rejected as `duplicate`. That includes rows that only become identical
after trimming and snapping.

### Scoring (gold documents only)

- Gold documents are the documents that appear in `gold.csv`. Only spans on gold
  documents are scored; an annotator with no accepted spans on gold documents gets no row.
- An annotator is scored against the gold spans of the gold documents **they annotated**
  (have at least one accepted span on).
- A span matches only on exact `start`, `end` **and** label. `tp` = matching spans,
  `fp` = their other spans, `fn` = relevant gold spans they did not match.
- `precision = tp / (tp + fp)`, `recall = tp / (tp + fn)`, `f1` = harmonic mean of the
  two (each 0.0 when its denominator is 0). Round each to 3 decimals; compute `f1` from
  the unrounded values.

### Report

`spanalign.reports.build_report()` returns:

- `export`: for each **non-gold** document with accepted spans, a list of
  `[start, end, label, annotator, text]`, sorted by start, then end, then annotator.
- `rejected`: reason → number of rejected rows.
- `accepted`: annotator → number of accepted spans (all documents).
- `scores`: annotator → `tp`, `fp`, `fn`, `precision`, `recall`, `f1`.
- `confusions`: across all annotators, spans whose offsets exactly match a gold span but
  whose label differs, counted as `[gold_label, annotator_label, count]`. Sorted by
  count (highest first), then gold label, then annotator label (alphabetical).
- `gold_labels`: canonical label → number of gold spans.

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
