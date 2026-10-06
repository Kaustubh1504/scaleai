# NER Span Merger

Three annotators marked named entities (people, organisations, places) in ten short
documents by character offsets. This tool checks every span against the document text,
cleans up each annotator's overlapping spans, and keeps the entities that at least two
annotators agree on.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/docs.json`: `doc_id` and `text` for each document.
- `data/annotations.csv`: one row per span: `doc_id`, `annotator`, `start`, `end`,
  `label`, `quote` (the text the annotator saw highlighted).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Offsets

1. Offsets are 0-based character indexes into the document text. In the CSV, `start` is
   the first character of the span and `end` is the **last** character of the span
   (inclusive): `Maria` at the start of a text is `start=0, end=4`.
2. Internally and in the report, spans are half-open: `end` is one past the last
   character, so the span covers `text[start:end]`.

### Cleaning

3. Doc ids and annotator ids: trim and lower-case. Labels: trim and upper-case. Quotes:
   trim.
4. A span is **misaligned** when its document is unknown or the text it covers is not
   exactly its (trimmed) quote. Misaligned spans are reported and otherwise ignored.
5. Within one annotator's spans on one document, a span that overlaps a strictly longer
   span is dropped. Two spans overlap when they share at least one character; spans that
   only touch (`[0, 5)` and `[5, 9)`) do not overlap.

### Consensus

6. Kept spans from different annotators vote together when their `start` and `end` are
   identical. A span position with at least **2** annotators becomes an entity; `votes` is
   the number of annotators.
7. The entity's label is the most common label among those annotators; a tie goes to the
   alphabetically first label.
8. The entity's `text` is the document text it covers.

### Report

`spanmerge.report.build_report()` returns:

- `kept`: annotator → doc id → list of `[start, end, label]` (half-open), sorted by
  start, longer first at the same start;
- `misaligned`: sorted `(doc_id, annotator, quote)` tuples;
- `entities`: doc id → list of `{text, label, start, end, votes}` sorted by position, for
  every document that has at least one entity;
- `label_counts`: label → number of entities.

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
