# set-057 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What is the flow inside build_report()?

`load_docs` builds doc_id -> text, `read_spans` turns spans.csv rows into cleaned Span objects, `candidates` groups them by (doc, start, end, label) and keeps groups with at least MIN_VOTES distinct annotators, then `resolve_doc` picks the non-overlapping entities for each doc. The summary is computed from the resolved entities.

### 2. What does read_spans skip?

Rows whose doc id (trimmed, upper-cased) is not in docs.json, rows where start or end isn't an integer, and anything for which make_span returns None (bad label, out-of-bounds offsets, empty after trimming).

### 3. What does to_zero_based return for each tool?

For `legacy` it returns a shifted `(start, end)` pair computed in its `if` branch; for any other tool it returns the inputs unchanged.

### 4. How are votes counted in candidates()?

A dict keyed by (doc_id, start, end, label) holds a set of annotator ids, so repeat marks by the same (lower-cased) annotator count once. Groups are iterated in sorted key order, so each doc's candidate list is in (start, end, label) order.

### 5. What counts as an overlap?

`_overlaps(a, b)` is `a.start < b.end and b.start < a.end` on exclusive ends, so spans that only touch (one ends where the other starts) do not overlap.

### 6. What does the annotators field count?

The number of distinct lower-cased annotator ids among the spans returned by read_spans, i.e. after cleaning but before voting.
