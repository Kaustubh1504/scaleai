# set-092 interviewer notes

**Scenario:** An asyncio client lists a paginated vector index per collection, skips documents whose SHA-1 is unchanged, embeds the rest in concurrent batches (semaphore-limited, retried on 429/5xx), records failed batches without stopping the run, and reports index entries to delete plus token cost.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Datetimes encoded with str() instead of ISO 8601

1. **Nudge:** Only the updated_at values in the request body differ. Where do datetimes become strings?
2. **Area:** Look at the hook json.dumps uses for objects it cannot encode itself.
3. **Exact:** _json_default returns str(value); it should return value.isoformat().

### B2: Fresh semaphore per request

1. **Nudge:** The server saw more requests in flight than max_concurrency. Where is concurrency supposed to be limited?
2. **Area:** Look at which semaphore _bounded acquires, and which one embed_all creates.
3. **Exact:** _bounded must use the shared semaphore: `async with self._limit:`.

### B3: Backoff sleep never awaited

1. **Nudge:** The retries happen, but no delays were recorded. Did the sleep ever actually run?
2. **Area:** Look at the line in with_retries that waits between attempts. Check the warnings in the test output.
3. **Exact:** Add the await: `await sleep(policy.delay(attempt, response))`.

### B4: Last page of the index listing dropped

1. **Nudge:** p06 and p88 are in the index but not in to_delete. Did the client ever see them?
2. **Area:** Trace list_index for policies: three pages are requested. Which page's items end up in `items`?
3. **Exact:** Extend items before checking next_page_token: move `items.extend(page["items"])` above the break.

### B5: Failed batches filtered out of the gather results

1. **Nudge:** products-1 was tried 3 times and never succeeded, yet nothing is reported as failed. Where did that error go?
2. **Area:** Follow what embed_all returns into run_sync's loop over zip(batches, outcomes).
3. **Exact:** Return the gather results unchanged: `return await asyncio.gather(..., return_exceptions=True)`.

### B6: Integer division in the cost

1. **Nudge:** total_tokens is right but the cost is zero. What is 91 tokens in thousands?
2. **Area:** Look at the cost formula in reports.summarize.
3. **Exact:** Use true division: total_tokens / 1000 * price_per_1k_tokens.

## "Why did that fix work?" probes

**B1**
- What would have happened if there were no default hook at all?
- How would a set or a Decimal in the payload behave with this hook?

**B2**
- Why does every result still come out right with no limit at all?
- Why is the semaphore created inside embed_all rather than at import time or in a default argument?

**B3**
- Why did the attempt counts stay right even though nothing waited?
- In production (real asyncio.sleep), what would this do to a rate-limited API?

**B4**
- Why didn't faq and products notice anything?
- Why did the skipped documents still come out right?

**B5**
- What would happen if return_exceptions were False instead?
- If the failing batch were first rather than last, what else would break with this filter?

**B6**
- For which token totals would this formula still give the right answer?
- Why round only at the end rather than rounding the thousands first?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `embedsync/documents.py` → `latest_by_id`: The `>=` looks like it lets an equal timestamp overwrite, and it does, which is the spec: on equal timestamps the later row in the file wins. It compares parsed datetimes, so the three formats order correctly.
- `embedsync/transport.py` → `_send_sync`: Catching HTTPError looks like it swallows failures, but it turns them into a Response carrying the real status code, which the retry loop and embed_batch then check. Nothing is lost.
