# set-052 interviewer notes

**Scenario:** Batch help-centre documents per collection, embed them concurrently under a semaphore with retries, normalise vectors per collection, then total tokens from the paginated usage API. Test 3 is the run summary.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Fresh semaphore per request

1. **Nudge:** The server saw more simultaneous requests than max_concurrency allows. What is supposed to stop that?
2. **Area:** Look at the `async with` in embed_batch: which semaphore does each task acquire?
3. **Exact:** Use the shared `self.limit` instead of creating asyncio.Semaphore(...) inside the call.

### B2: Backoff sleep never awaited

1. **Nudge:** The retries happened, but no waits were recorded. Did the client ever wait?
2. **Area:** Look at how send_with_retries calls sleep. What does calling an async def return?
3. **Exact:** Add `await` before sleep(wait_time(...)).

### B3: Only 5xx treated as failure

1. **Nudge:** kb-02 got HTTP 422 but its status says ok. What decides ok vs failed?
2. **Area:** Look at the status check right after the retries in embed_batch.
3. **Exact:** `response.status >= 500` should be `response.status != 200`.

### B4: Collection options merged into shared defaults

1. **Nudge:** Only the kb vectors differ, and they look normalised. What does kb's config say?
2. **Area:** Follow `options` in embed_batch: is it a fresh dict per call, and when is `normalize` read compared with when it was set?
3. **Exact:** Copy the defaults: options = dict(self.defaults).

### B5: First usage page dropped

1. **Nudge:** Three usage pages were requested, but the token total is short. Which records were counted?
2. **Area:** Look at what fetch_usage does with the very first page.
3. **Exact:** Start with records = list(page["data"]).

### B6: Shared default dict in tally

1. **Nudge:** Every collection shows the same numbers. Are they really separate dicts?
2. **Area:** Look at tally's signature.
3. **Exact:** Use counts=None and create a new dict inside the function.

## "Why did that fix work?" probes

**B1**
- Why does a semaphore only limit concurrency if every task shares the same instance?
- Why didn't attempts or vectors change when the limit was missing?

**B2**
- Why did every other test still pass when no wait happened?
- Where in the test output could you have spotted this without reading the code?

**B3**
- Why didn't the summary's embedded count change?
- Which statuses can reach that check at all, given the retry loop?

**B4**
- Why is the result deterministic even though the tasks run concurrently?
- Would this still happen if max_concurrency were 1? Why or why not?

**B5**
- Why does the shortfall vary from run to run?
- How would you restructure the loop so the first page can't be forgotten?

**B6**
- Why are the numbers even bigger than the whole run's totals?
- If you ran test_3 on its own, would the numbers be the same? Why?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `embedindex/retry.py` → `wait_time`: Retry-After wins when present, otherwise backoff × 2**attempt with attempt starting at 0, exactly as the README says. `2 ** attempt` without parentheses is fine because ** binds tighter than *.
- `embedindex/indexer.py` → `make_batches`: groupby is only safe on sorted input, and it is sorted by collection first. sorted() is stable, so documents keep their file order inside each collection, and numbering starts at 01 per collection.
