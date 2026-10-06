# set-076 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What happens inside run_job, step by step?

It loads config, keeps only enabled collections, loads documents (collecting skipped ids), builds batches with make_batches, and starts every embed_batch with asyncio.gather. Then it builds the accepted list from OK results, calls client.commit, and finally calls collect_index once per collection that had a batch.

### 2. How does the mock server decide what to return for a batch?

SCRIPT maps a batch_id to a list of (status, headers, dims_override) steps, served in order with the last step repeating. Batches not in SCRIPT always get 200. It sleeps 30 ms per embeddings request and tracks the peak number of requests being handled at once in max_in_flight.

### 3. How does the vectors listing endpoint page its results?

It sorts the collection's stored ids, applies offset and min(limit, MAX_PAGE) where MAX_PAGE is 3, and returns {items, has_more}, where has_more is offset + len(items) < total. Seeded vectors (faq-legacy-1/2, pol-100) are included.

### 4. What does the sleep recorder in the tests capture?

tests/_harness.py passes a SleepRecorder as `sleep`. It is an async callable that appends each delay to `delays` and returns at once, so the tests never really wait. EmbeddingClient stores it as self.sleep and passes it to send_with_retries.

### 5. What does parse_retry_after return?

It scans the headers case-insensitively for Retry-After. A numeric value comes back as a float clamped at 0.0 or more, a non-numeric value as None, and a missing header as None.

### 6. How is a batch classified as ok, failed or rejected?

client.interpret: a non-200 final response is FAILED with that status. A 200 is OK when `data` has one entry per input document and every embedding length equals the collection's dimensions, otherwise REJECTED.

### 7. What is BatchStatus and where is REQUEUE_STATUSES used?

BatchStatus is a plain enum.Enum with values ok/failed/rejected, defined in models.py with REQUEUE_STATUSES just below it. reports.build_report uses REQUEUE_STATUSES as a membership test on r.status to build the requeue list.
