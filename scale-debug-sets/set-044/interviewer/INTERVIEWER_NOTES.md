# set-044 interviewer notes

**Scenario:** An asyncio client embeds guideline snippets in batches against a mock /v1/embeddings endpoint (bounded concurrency, Retry-After/backoff retries, failed batches reported), then pages through a cursor-paginated index listing to find stale ids.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Fresh semaphore created per batch

1. **Nudge:** The server saw more than 2 requests in flight. What is supposed to stop that?
2. **Area:** Look at which semaphore _run_batch acquires.
3. **Exact:** Use `async with self._sem:` instead of creating a new Semaphore per call.

### B2: Backoff sleep never awaited

1. **Nudge:** b2's second attempt arrives about 50 ms after the first, but the server asked for 0.2 s. Check the warnings in the test output.
2. **Area:** Look at the wait between attempts in post_with_retries.
3. **Exact:** Add `await` before asyncio.sleep(...).

### B3: One retry too many

1. **Nudge:** b4 was sent 4 times. How many attempts does the README allow with max_retries = 2?
2. **Area:** Trace attempt through the loop in post_with_retries for a batch that always returns 503.
3. **Exact:** Stop when attempt >= max_retries.

### B4: Exceptions from gather silently skipped

1. **Nudge:** `failed` is empty, but b4 and b6 have no vectors. Where did their errors go?
2. **Area:** Follow what embed_all does with each item gathered from the batches.
3. **Exact:** Record `failed[batch.id] = str(result)` before `continue`.

### B5: Token total snapshotted before the await

1. **Nudge:** total_tokens is lower than the sum of the successful batches' usage. Which update is getting lost?
2. **Area:** Look at when _embed_batch reads self.usage_tokens versus when it writes it.
3. **Exact:** Do `self.usage_tokens += body["usage"]["total_tokens"]` after the response, without the earlier snapshot.

### B6: Last index page dropped

1. **Nudge:** Three index pages were requested, yet d27 and d40 never appear. Which page are they on?
2. **Area:** Look at the order of statements in list_index_ids' loop.
3. **Exact:** Extend ids before checking next_cursor and breaking.

## "Why did that fix work?" probes

**B1**
- Why are all the results still correct even though the limit was ignored?
- Where must a semaphore be created for it to limit a group of tasks?

**B2**
- Why didn't the attempt counts change?
- What would time.sleep() there do to the other batches?

**B3**
- Why is b4 still reported as 'HTTP 503' either way?
- Why did b2 (one 429, then 200) have the right count?

**B4**
- What would happen without return_exceptions=True if b6 raised first?
- Why does missing_docs in the summary still list the right ids?

**B5**
- Why is `+=` safe here in asyncio when it wouldn't be with threads?
- Why does the lost amount depend on how the batches overlap?

**B6**
- Why does test_index_listed_page_by_page pass with this code?
- What would change if the index had exactly 8 ids?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `embedclient/retry.py` → `backoff_delay`: It returns Retry-After as a float when present (the spec allows fractional values), else base × 2^attempt with attempt starting at 0, so the first fallback wait is exactly backoff_seconds. `2 ** attempt` binds tighter than `*`, so the expression is base * (2 ** attempt).
