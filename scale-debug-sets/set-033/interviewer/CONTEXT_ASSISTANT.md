# set-033 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What happens to a span row between the CSV and vote()?

`load_spans` skips rows whose annotator isn't registered, then `normalise` cleans ids and the label, rejects unknown docs or labels, converts `end` with `to_exclusive_end` for the annotator's tool, checks the bounds, trims whitespace with `trim`, and builds a `Span`. Valid spans are kept in file order; invalid rows are counted per annotator.

### 2. What is Span.key?

A tuple `(doc_id, start, end, label)`, defined as a property in models.py. Both consensus and metrics compare spans through it.

### 3. How does vote() count votes?

It sorts the spans, walks them with `itertools.groupby` keyed on `s.key`, builds a set of annotators for each group and stores the set's size in `accepted` when it is at least `MIN_VOTES` (2).

### 4. Where is the entity text built?

In `reports.entities_by_doc`, which slices the document text using the accepted span's start and end and stores it with the label and vote count. Entities are then sorted by (start, end).

### 5. How is agreement computed?

`metrics.agreement` collects the keys of each annotator's valid spans, counts how many of those keys are in `accepted`, and divides by the number collected, rounded to 3 decimals.

### 6. What does trim() do with ' Paris'?

It advances `start` while the character at `start` is whitespace and pulls `end` back while the character before `end` is whitespace, so a span starting on the space before 'Paris' ends up covering just 'Paris'.
