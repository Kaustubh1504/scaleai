# set-028 interviewer notes

**Scenario:** An asyncio client embeds deduped documents with two models in turn (semaphore-limited batches, retries with injectable async sleep, (model, text) cache), then pages through a usage ledger whose pages can be short.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Semaphore created but never acquired

1. **Nudge:** What enforces max_concurrency in this client?
2. **Area:** Find where self.sem is used.
3. **Exact:** Wrap the send_with_retries call in `async with self.sem:`.

### B2: Backoff sleep never awaited

1. **Nudge:** The retries still happen, but no delays are recorded. What does calling an async function return?
2. **Area:** Look at the sleep call in send_with_retries.
3. **Exact:** Add `await` before sleep(...).

### B3: Cache key ignores the model

1. **Nudge:** embed-l made only one request. Why did it think everything else was cached?
2. **Area:** Look at what goes into the cache key.
3. **Exact:** Include the model in the hashed key: f"{model}\n{text}".

### B4: One retry too few

1. **Nudge:** How many attempts does README rule 3 allow with max_retries 2?
2. **Area:** Count the iterations of the retry loop.
3. **Exact:** Use range(policy.max_retries + 1).

### B5: Final 4xx treated as a success

1. **Nudge:** d09/d11/d12 fail, but with http_status None. What did the server actually return?
2. **Area:** Look at which statuses embed_batch treats as failures.
3. **Exact:** Raise EmbeddingError for any status other than 200.

### B6: Short usage page treated as the last

1. **Nudge:** Only one usage page was requested. What does the README say about short pages?
2. **Area:** Look at the loop's exit condition in collect_usage.
3. **Exact:** Stop only when next_cursor is None.

## "Why did that fix work?" probes

**B1**
- Why do all the other tests still pass with unlimited concurrency?
- Should the retry sleep happen while holding the semaphore? What are the trade-offs?

**B2**
- Why didn't this raise an exception?
- What would a real provider do to a client that retries with no delay?

**B3**
- Why did exactly d09, d11 and d12 get 8-dim vectors?
- Name another parameter that belongs in an embedding cache key in real systems.

**B4**
- Why was this invisible while the cache key ignored the model?
- Why are the recorded backoff delays the same with and without this change?

**B5**
- Why are the document counts in test 3 still right?
- Why is reusing RETRYABLE here tempting, and why is it the wrong set?

**B6**
- Why does embed-s show 0 billed tokens rather than a smaller number?
- If the server didn't cap pages, when would this code still lose data?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `embedq/retry.py` → `wait_time`: `2 ** attempt` with attempt starting at 0 gives backoff, 2×backoff, ... exactly as rule 3 says, and Retry-After takes priority when present.
- `embedq/transport.py` → `request_json`: It runs the blocking urllib call in a worker thread via asyncio.to_thread and awaits it, which is what lets batches overlap. HTTP error statuses come back as Response objects, not exceptions.
