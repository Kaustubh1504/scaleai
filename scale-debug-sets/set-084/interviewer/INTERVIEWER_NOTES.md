# set-084 interviewer notes

**Scenario:** An asyncio client submits document batches as embedding jobs (bounded concurrency), retries 429/5xx creates with Retry-After or exponential backoff, polls jobs to completion, pages through results by token, and reports norms plus every failed batch.

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

1. **Nudge:** How many requests were in flight at the peak, and how many batches are there?
2. **Area:** Look at what run_one acquires before starting a batch.
3. **Exact:** Use the shared `sem`: `async with sem:`.

### B2: Transient handler shadows RateLimited

1. **Nudge:** legal/1 is retried, but how long does it wait compared with what the server asked for?
2. **Area:** Look at the class hierarchy in errors.py and the order of the except clauses in retry.py.
3. **Exact:** Put `except RateLimited` before `except TransientError`.

### B3: max_attempts excludes the first try

1. **Nudge:** How many create requests did product make, and what did the last one return?
2. **Area:** Follow where create_with_retries gets its number of attempts.
3. **Exact:** max_attempts should be max_retries + 1.

### B4: Poll pause never awaited

1. **Nudge:** news/1 was polled four times, yet no poll waits were recorded. Any warnings in the output?
2. **Area:** Look at how the poll loop pauses between checks.
3. **Exact:** `await self.pause(...)`.

### B5: Failed batches dropped after gather

1. **Nudge:** The support documents aren't embedded, but failures is empty. Where did the exception go?
2. **Area:** Look at what happens to each gather outcome in run_batches.
3. **Exact:** Record exceptions: failures[batch.label] = getattr(outcome, 'reason', ...).

### B6: Next page read from the echoed token

1. **Nudge:** Only one FAQ document is missing. Which batch is it in, and how many results pages does that batch have?
2. **Area:** Look at which field the results loop takes the next token from.
3. **Exact:** Use next_page_token.

## "Why did that fix work?" probes

**B1**
- Why does every result still come out right without the limit?
- Why must the semaphore be created once, outside run_one?

**B2**
- Why does the retry still succeed, just with the wrong delay?
- How could a real server punish a client that ignores Retry-After?

**B3**
- Why does legal/1 still succeed with this slip?
- Where does the product failure show up besides this test?

**B4**
- Why did the job still complete correctly?
- What would this do to a real API's rate limit?

**B5**
- What would happen without return_exceptions=True if one batch failed?
- Why is silently dropping a failed batch worse than crashing?

**B6**
- Why are all the other batches complete?
- What data change would have exposed this in more than one batch?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `embedjobs/transport.py` → `send`: Catching HTTPError and returning a Response looks like it hides errors, but it is deliberate: status handling happens in raise_for_status, and HTTPError (a URLError subclass) is the only exception that carries a status and body.
- `embedjobs/errors.py` → `retry_after_seconds`: The header is in seconds and the body field in milliseconds, so only the body value is divided by 1000. `is not None` keeps a legitimate 0 ms.
