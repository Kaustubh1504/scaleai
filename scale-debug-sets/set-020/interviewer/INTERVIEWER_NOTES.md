# set-020 interviewer notes

**Scenario:** An asyncio client submits one batch job per shard to a mock tagging API, polls each job, reads its page-numbered results, archives it, and routes low-confidence labels to review. At most max_concurrency shards run at once. Test 3 is the token/cost summary.

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

1. **Nudge:** The server saw more than two submits at the same time. What is supposed to limit that?
2. **Area:** Follow the `limit` object from run_all into run_shard.
3. **Exact:** Wrap the call in `async with limit:`.

### B2: archive() coroutine never awaited

1. **Nudge:** The server never received a single DELETE. Look at stderr while the tests run.
2. **Area:** Find where archive() is called.
3. **Exact:** Add `await` in front of client.archive(batch_id).

### B3: Last results page never fetched

1. **Nudge:** Only R10 is missing, and it's the 7th result of S2. How many pages does S2 have?
2. **Area:** Look at the loop that reads pages after the first.
3. **Exact:** Use range(2, total_pages + 1).

### B4: Score equal to the threshold sent to review

1. **Nudge:** R12 has a score of exactly 0.7. What does the spec say about that?
2. **Area:** Look at the threshold comparison in classify.
3. **Exact:** Use score >= threshold.

### B5: Request ids trimmed but not upper-cased

1. **Nudge:** S5 has an `r17` key and an `unknown` label. Look at that row in requests.csv.
2. **Area:** Compare how request ids and shard ids are cleaned in the loader.
3. **Exact:** Use norm_id for the request id.

### B6: Tokens rounded to whole thousands before pricing

1. **Nudge:** 8815 tokens at $0.02 per 1k is not 0.18.
2. **Area:** Look at where rounding happens in the cost formula.
3. **Exact:** Multiply first, then round(..., 4).

## "Why did that fix work?" probes

**B1**
- Why did every result still come out right without the limit?
- Why does the semaphore have to cover the whole shard (submit to archive) and not just the submit call?

**B2**
- What does calling an async function without await actually return?
- Why did nothing else in the run change?

**B3**
- Why didn't any other shard lose results?
- Which page numbers does the loop request for total_pages = 3, before and after the fix?

**B4**
- Why is R13 (0.69) needs_review both before and after the fix?
- Is comparing floats with >= safe here? Where does 0.7 come from?

**B5**
- Why did ` R03` in S1 come through fine?
- Why did the mock answer `unknown` instead of an error?

**B6**
- How large could the error be per run with the old formula?
- Why does total_tokens pass while cost_usd fails?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `labelbatch/transport.py` → `_blocking_send`: It is the blocking urllib call that `send` runs in a worker thread via asyncio.to_thread. HTTP errors are caught and returned as Response objects with their status, headers and decoded body, so callers can check the status themselves.
- `labelbatch/client.py` → `poll_delay`: Returning 0 for attempt 0 looks like it ignores the interval, but it only skips the wait before the first poll. Every later poll waits poll_interval_s, so there are exactly max_polls status calls spaced as rule 2 says.
