# set-046 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What happens inside build_report(), in order?

It builds a ThresholdTable from thresholds.csv, loads and de-duplicates predictions, loads reviewers, routes every prediction (`route_all`), builds the human queue (`review_queue`), assigns it (`assign`, which appends into each Reviewer's `assigned` list and returns the unassigned ids), computes SLA due times for the queue, and runs `calibrate` over reviews.csv.

### 2. How does ThresholdTable find a threshold?

`_resolve` checks the exact `(model_version, label)` row, then the model's `*` row, then falls back to DEFAULT_THRESHOLD (0.90). `lookup` wraps `_resolve` with a dict cache stored on the instance, so each key is resolved once per table.

### 3. What does Reviewer.remaining return?

`capacity - len(assigned)`, computed live from the reviewer's `assigned` list, so it shrinks as `assign` hands out items.

### 4. How does pick_reviewer break ties?

It filters to active reviewers who speak the item's language and have `remaining > 0`, then takes `min` by `(-remaining, id)`: most remaining capacity first, then lowest id.

### 5. Which reviews does calibrate() use?

Only rows whose cleaned `human_label` is non-empty. Those feed `agreement_rates`, `reviewer_mix` and the max of `finished_at`.

### 6. How does the loader read capacity and active?

`load_reviewers` reads `capacity` from each JSON entry and converts it to int, using DEFAULT_CAPACITY (2) when it has no usable value. `active` is True only when the JSON value is literally `true`, defaulting to True when the key is missing.

### 7. What is in the sla section and what type are its values?

One entry per item in the review queue (human decisions only), mapping item id to `received_at + SLA_HOURS[priority]` as a `datetime`. `export_json` is what turns those into strings.
