# set-081 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do, step by step?

It loads documents, label aliases and gold spans, reads the annotation rows, then calls `spans.normalize_all` to clean them into `Span` objects plus a Counter of rejection reasons. It then builds the export (non-gold docs), accepted counts, `scoring.score_annotators`, the ranked confusions and the gold label counts.

### 2. How is a single annotation row turned into a Span?

`Normalizer.normalize` looks up the document, resolves the label via `resolve_label`, parses both offsets, checks `0 <= start < end <= len(text)`, calls `trim_whitespace`, then `tokens.snap` with the cached tokens for that document. Any `SpanError` raised along the way carries the rejection reason.

### 3. What does tokenize return for "Dr. Kenji"?

Three `Token` objects: `Dr` (0, 2), `.` (2, 3) and `Kenji` (4, 9). The end offsets come straight from `re.finditer`.

### 4. How are duplicates detected?

`normalize_all` keeps a set of accepted `Span` dataclass instances (frozen, so hashable). A cleaned span equal to one already in the set increments `rejected["duplicate"]` and is not added.

### 5. What is in the gold list and how is it keyed?

`read_gold` returns tuples `(doc_id, start, end, LABEL)`. `score_annotators` uses them as a set, and `confusion_counts` builds a dict keyed by `(doc_id, start, end)` mapping to the gold label.

### 6. Which annotators appear in the scores table?

One row for each annotator key in `predicted`, sorted by id. `predicted` is filled inside `score_annotators` from the spans its loop iterates over.

### 7. How is the export ordered?

`export_spans` sorts all spans by `(doc_id, start, end, annotator)`, skips gold documents, and groups the rest per doc id with the text slice `docs[doc_id][start:end]`.
