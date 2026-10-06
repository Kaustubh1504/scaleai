# set-009 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do, in order?

It loads docs.json into {doc_id: text}, loads annotations.csv into Span objects, calls `spans.clean_spans` to split them into kept spans per (annotator, doc) and misaligned spans, then `consensus.build_entities`, and finally builds the `kept`, `misaligned`, `entities` and `label_counts` fields.

### 2. What are Span.start and Span.end after loading?

Both are ints. `start` is the CSV `start`. `end` is computed from the CSV `end` in `load_spans`; `Span.length` is `end - start`, and `aligned` compares `text[span.start:span.end]` with the trimmed quote.

### 3. How does resolve_overlaps order and filter spans?

It sorts by `(start, -end)`, so at the same start the longer span comes first, then loops over the spans and removes any span for which some other span in the list is strictly longer and overlaps it. It returns the list it removed from.

### 4. What counts as a vote in build_entities?

Spans from all annotators on a doc are pooled. `votes[(start, end)]` is a dict of annotator → label, so one annotator counts once per position. Positions with at least MIN_VOTES (2) annotators become entities.

### 5. How is the entity label chosen?

`majority_label` builds a Counter of the voters' labels and takes `min` over `(-count, label)`, i.e. the highest count with an alphabetical tie-break.

### 6. Which docs appear in `entities`?

build_entities walks `sorted(docs)` and only adds a doc id when it found at least one entity for it.
