# set-076 interviewer notes

**Scenario:** An asyncio client batches knowledge-base documents per collection, embeds them with a concurrency cap and retries, commits the job, then pages through the vector index to check coverage. Test 3 is the report (index coverage and requeue list).

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

1. **Nudge:** The server saw more simultaneous requests than max_concurrency. What is supposed to stop that?
2. **Area:** Look at how embed_batch limits concurrency, and which semaphore object each call waits on.
3. **Exact:** `async with asyncio.Semaphore(...)` makes a fresh semaphore per call. Use the shared `self._slots`.

### B2: One attempt short on persistent 5xx

1. **Nudge:** Only policies-01 has the wrong attempt count. What is special about it?
2. **Area:** Count how many times the retry loop calls do_request when every response is 503.
3. **Exact:** range(max_retries) should be range(max_retries + 1).

### B3: Retry-After: 0 replaced by exponential backoff

1. **Nudge:** Which batch got Retry-After headers from the server, and what did it wait?
2. **Area:** Look at how backoff_delay picks between the header and the formula.
3. **Exact:** `hint or formula` treats 0.0 as missing. Check `hint is not None` instead.

### B4: Commit coroutine never awaited

1. **Nudge:** The server never received a commit. Does run_job ever actually send one?
2. **Area:** Look at the commit call in run_job and compare it with the other client calls there.
3. **Exact:** client.commit(...) is missing `await`.

### B5: Index offset advanced by requested page size

1. **Nudge:** Only faq is short, and the missing ids are in the middle of the sorted list. What does the server do with limit=5?
2. **Area:** Look at how collect_index works out the next offset.
3. **Exact:** Advance by len(items), not client.config.page_size.

### B6: Requeue statuses listed as strings

1. **Nudge:** Two batches failed and one was rejected, yet requeue is empty. Follow how requeue picks batches.
2. **Area:** Look at what r.status holds and what REQUEUE_STATUSES contains.
3. **Exact:** In models.py, use (BatchStatus.FAILED, BatchStatus.REJECTED) instead of the raw strings.

## "Why did that fix work?" probes

**B1**
- Why does a semaphore only limit anything if every task shares the same instance?
- Why did every result still come out right with no concurrency limit at all?

**B2**
- Why were the recorded backoff delays identical with and without this change?
- Why didn't faq-02 (two 429s, then 200) lose its success?

**B3**
- Why is None the right sentinel here and 0.0 not?
- What would `Retry-After: abc` produce, and does that match the spec?

**B4**
- Why doesn't a missing await raise an error here?
- Where in the test output could you have spotted this without reading the code?

**B5**
- Why were policies, changelog and pricing unaffected?
- Why is a cursor or next-token API safer than client-computed offsets?

**B6**
- Would this have worked if BatchStatus subclassed str? Why?
- Why did `counts` come out right while requeue did not?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `vecsync/transport.py` → `perform_request`: Returning error statuses as a Response instead of raising looks like it ignores HTTP failures, but the retry layer and interpret() both branch on response.status. Raising here would make retries impossible.
- `vecsync/loader.py` → `make_batches`: `-(-len(docs) // size)` is ceiling division, so a 7-document collection gives 3 batches and the slices cover every document exactly once. sorted() is stable, so equal dates keep file order as the spec requires.
