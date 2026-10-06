# set-012 interviewer notes

**Scenario:** An asyncio client embeds help-centre articles in batches under a concurrency limit, retries transient errors with Retry-After, classifies malformed responses, then pages through usage records (after=<last_id>) and reports token spend and near-duplicate articles.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: One retry too few

1. **Nudge:** Only the batch that never recovers has the wrong number of attempts. How many should it get with max_retries = 2?
2. **Area:** Look at the stop condition in retry.send_with_retries.
3. **Exact:** `attempts >= max_retries` should be `attempts > max_retries`.

### B2: Backoff sleep never awaited

1. **Nudge:** The retry for b02 arrives far sooner than its Retry-After header allows. Is the job waiting at all?
2. **Area:** Look at how the delay is applied in retry.py. Check the warnings in the test output.
3. **Exact:** Add `await` before `asyncio.sleep(...)`.

### B3: Semaphore created but never acquired

1. **Nudge:** The server saw far more simultaneous requests than max_concurrency. What is supposed to limit them?
2. **Area:** Find where self.semaphore is created, then look for where it is used.
3. **Exact:** Wrap the request in `_post` with `async with self.semaphore:`.

### B4: ValueError handler shadows JSONDecodeError

1. **Nudge:** d09 and d10 come back invalid, but their batch body was not even valid JSON. Which branch handles that?
2. **Area:** Look at the order of the except clauses in embed_batch.
3. **Exact:** Put `except json.JSONDecodeError` before `except ValueError`.

### B5: Usage cursor taken from the first record of the page

1. **Nudge:** total_tokens is far higher than the usage the server recorded. Look at which records come back on each page.
2. **Area:** Look at the cursor collect_usage sends for the next page.
3. **Exact:** Use `page["last_id"]`, not `page["first_id"]`.

### B6: Near-duplicates listed least similar first

1. **Nudge:** The right pairs are listed, but in reverse. What decides the order?
2. **Area:** Look at the sort key at the end of similarity.near_duplicates.
3. **Exact:** Negate the similarity: `key=lambda p: (-p[2], p[0], p[1])`.

## "Why did that fix work?" probes

**B1**
- Why were b02 and b03 unaffected by this?
- If the condition used a zero-based attempt index instead of a count, how would the comparison change?

**B2**
- Why does the code still run without an error when the await is missing?
- Why would time.sleep() here be a poor fix in an asyncio program?

**B3**
- Why is the semaphore taken per attempt rather than around the whole send_with_retries call?
- Would the results still be correct without the limit? Why does the limit matter against a real API?

**B4**
- How would you find out that JSONDecodeError is a ValueError without reading the docs?
- Name another standard-library pair where this ordering matters (hint: urllib).

**B5**
- Why did the loop still end instead of running forever?
- How could the client detect duplicate records even if the cursor was mishandled?

**B6**
- Why is `reverse=True` not an exact replacement for negating the similarity here?
- d01/d09 are 0.981 similar. Why are they not in the list?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `vecbatch/transport.py` → `_send`: HTTPError is caught and turned into a normal Response with the real status and headers, so 4xx/5xx reach the retry logic instead of raising. Network errors (URLError) are deliberately left to propagate.
- `vecbatch/pipeline.py` → `make_batches`: `range(0, len(docs), size)` with `docs[start:start + size]` covers every document exactly once and allows a short final batch; `enumerate(..., start=1)` gives b01, b02, ... as the spec requires.
