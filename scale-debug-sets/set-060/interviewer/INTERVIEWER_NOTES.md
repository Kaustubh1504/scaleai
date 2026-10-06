# set-060 interviewer notes

**Scenario:** An asyncio client pages through a dataset API, selects records, embeds them in concurrent batches (semaphore, retries with backoff), classifies each batch result, and commits ok batches to a vector index via gather. Test 3 is the run report (commit outcome, tokens).

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Last page's records dropped

1. **Nudge:** fetched is 25 but the dataset has 27 records, and all 6 pages were requested. Which records are missing?
2. **Area:** Look at the order of operations inside fetch_all's loop.
3. **Exact:** Extend records with the page before checking for the end.

### B2: Semaphore created but never acquired for embeddings

1. **Nudge:** The server saw more simultaneous embedding requests than max_concurrency. Where is the limit enforced?
2. **Area:** Find where self.sem is used, and where it isn't.
3. **Exact:** Wrap the _send_embeddings call in `async with self.sem:`.

### B3: Backoff sleep never awaited

1. **Nudge:** b2's retries arrive about 0.05 s apart. How long should the client wait?
2. **Area:** Look at what with_retries does between attempts. Check the warnings in the test output.
3. **Exact:** await the asyncio.sleep call.

### B4: 4xx responses passed to the parser

1. **Nudge:** b5 got HTTP 400. Why does its status say bad_response?
2. **Area:** Look at how embed_batch decides a response failed.
3. **Exact:** Treat any status >= 400 as http_error.

### B5: Base ResponseError caught before DimensionMismatch

1. **Nudge:** b4's vectors have 3 dims, but its status is bad_response. Which exception does parse_embeddings raise?
2. **Area:** Look at the class hierarchy in parsing.py and the order of the except clauses.
3. **Exact:** Put `except DimensionMismatch` before `except ResponseError`.

### B6: One upsert failure hides every commit outcome

1. **Nudge:** commit says nothing was committed, but the index accepted three batches. Where are their outcomes?
2. **Area:** Look at how commit() collects the upsert results.
3. **Exact:** Pass return_exceptions=True to asyncio.gather.

## "Why did that fix work?" probes

**B1**
- Why didn't the missing records change any batch or vector?
- What would happen with this code if the dataset fit in a single page?

**B2**
- Why did every result still come out right without the limit?
- Should the semaphore be held during the retry backoff sleeps? What are the trade-offs?

**B3**
- Why does the attempt count stay right even though no waiting happens?
- What would time.sleep() do here instead, and why is that worse?

**B4**
- Why wasn't b5 retried either way?
- Which other status codes would have slipped through this check?

**B5**
- Why does the order of except clauses matter only for related classes?
- How would you have caught this with a linter or a test?

**B6**
- Why does commit() check isinstance(outcome, UpsertError) separately from other exceptions?
- With the bug, did the b1-b3 upserts actually reach the server?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `vecsync/retry.py` → `backoff_delay`: `2 ** (attempt - 1)` looks like an off-by-one next to the README's backoff_s x 2^(n-1), but attempt is 1-based here (with_retries increments before calling), so the first wait is backoff_s and the second is 2 x backoff_s, exactly as specified. Retry-After takes precedence, including '0'.
