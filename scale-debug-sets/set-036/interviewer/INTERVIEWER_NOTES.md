# set-036 interviewer notes

**Scenario:** An asyncio client embeds a document corpus in concurrent batches against a local embeddings endpoint (bounded concurrency, 429/5xx retries), upserts every vector into a vector index, and reports token usage and near-duplicate documents.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Fresh semaphore per batch

1. **Nudge:** The server saw more than 2 requests in flight. Where is the limit supposed to be enforced?
2. **Area:** Compare how embed_batch and upsert acquire their limit.
3. **Exact:** Use the shared self.limit in embed_batch instead of constructing a Semaphore there.

### B2: One attempt short of max_retries + 1

1. **Nudge:** Batch 2 always gets 503. How many times does the README say it should be tried?
2. **Area:** Look at the loop bound in send_with_retries.
3. **Exact:** Use range(policy.max_retries + 1).

### B3: Backoff sleep never awaited

1. **Nudge:** The recorder saw no waits at all, but retries did happen. Is the sleep reached?
2. **Area:** Look at how send_with_retries calls sleep. Scroll up in the test output for a RuntimeWarning.
3. **Exact:** Put await in front of sleep(...).

### B4: Rejected upserts counted as stored

1. **Nudge:** The server answered d07 with 409. Where does that error go after gather returns?
2. **Area:** What does asyncio.gather(..., return_exceptions=True) put in the results list for a failed coroutine?
3. **Exact:** Check isinstance(result, Exception) instead of result is None.

### B5: Average tokens floored

1. **Nudge:** 208 / 14 is not a whole number. Why is the report showing an int?
2. **Area:** Look at the tokens_per_doc line in reports.py.
3. **Exact:** Use round(run.total_tokens / embedded, 2).

### B6: Similarity rounded before the threshold check

1. **Nudge:** Compute the cosine for d15 and d16 yourself. Is it at least 0.95?
2. **Area:** Look at where near_duplicates rounds.
3. **Exact:** Compare the raw cosine with the threshold; round only when appending.

## "Why did that fix work?" probes

**B1**
- Why does a semaphore created inside the coroutine never block anything?
- The semaphore is held while the retry loop sleeps. Is that what you want? What changes if it is released between attempts?

**B2**
- With the off-by-one, the client slept after its final attempt. Why didn't the waits test catch that?
- If batch 2 had succeeded on its 4th attempt, which other tests would have failed?

**B3**
- Against the real API, what would the server have seen with this line as it was?
- How would you make the tests fail loudly on 'coroutine was never awaited' warnings?

**B4**
- What would happen to the whole run if return_exceptions were False?
- embed_documents re-raises unexpected exceptions but index_vectors does not. Which behaviour would you choose here and why?

**B5**
- Why is the denominator embedded documents rather than all 18 loaded documents?
- What would // give for negative numbers, and why does that matter in other reports?

**B6**
- Why does d05/d14 still report 0.98 either way?
- When is it safe to round a value before comparing it?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `vecsync/loader.py` → `batched`: range(0, len(items), size) steps through every start index and items[i:i + size] clamps at the end of the list, so the last short batch (d17, d18) is kept and nothing is duplicated.
- `vecsync/retry.py` → `wait_time`: Retry-After wins when present; otherwise backoff * 2 ** attempt. ** binds tighter than *, so this is backoff * (2 ** attempt): 0.5, 1.0, 2.0 for attempts 0, 1, 2, exactly as the README says.
