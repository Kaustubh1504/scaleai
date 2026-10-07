# set-028 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does run() do, in order?

It loads config and documents, creates one EmbeddingClient (with the injected sleep if given), awaits `embed_model` for each model in config order, then awaits `collect_usage`, and builds the per-document rows and the summary from the client's cache, the failure maps and the usage records.

### 2. How does embed_model decide what to send?

It takes `unique_texts(docs)`, keeps texts for which `(model, text) not in self.cache`, splits them with `batched(pending, batch_size)`, and gathers `embed_batch` for every batch with `return_exceptions=True`.

### 3. What does VectorCache.__contains__ expect?

A `(model, text)` tuple. It computes `self.key(model, text)` and checks the internal dict. `get` and `put` use the same `key` helper.

### 4. How are exceptions from batches turned into document results?

In `embed_model`, an EmbeddingError becomes `failed` with its status and a reason of transient/rejected based on RETRYABLE. Any other exception becomes `failed` with `http_status` None and reason `invalid_response`. Every text in that batch gets the same failure dict.

### 5. How does the mock server behave for the usage endpoint?

It sorts all usage records by (model, first input text), caps the page at 4 records whatever `limit` is, and returns a base64 offset cursor in `next_cursor`, or null when there is nothing after this page.

### 6. What does parse_vectors return?

The `embedding` lists from `body['data']` sorted by each item's `index`. It raises ValueError if `data` is missing or its length differs from the number of inputs.

### 7. How do the tests observe the retry waits?

test_1 passes `sleep=record_sleep`, an async function that appends its argument to a list and returns, so no real time passes. The test compares the sorted list.
