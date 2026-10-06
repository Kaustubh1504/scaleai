# set-068 interviewer notes

**Scenario:** An asyncio client batches documents to a mock embeddings endpoint behind a semaphore, retries transient errors with Retry-After/backoff, matches response items by index, and summarises norms and token usage.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: datetime serialised with str()

1. **Nudge:** Compare the newest_update the server received with the README example character by character.
2. **Area:** json.dumps can't encode datetime itself. Look at the `default` hook passed in encode_body.
3. **Exact:** _encode_value returns str(value); return value.isoformat().

### B2: Fresh semaphore per batch

1. **Nudge:** The server saw more than 2 requests at the same time. What is supposed to cap that?
2. **Area:** Find where a semaphore is acquired in client.py, and which semaphore it is.
3. **Exact:** Use the shared `async with self._limit:` created in __init__.

### B3: Retry loop one attempt short

1. **Nudge:** b04 always gets 503. How many times should it be tried with max_retries = 2?
2. **Area:** Look at the loop bounds in send_with_retries.
3. **Exact:** Loop over range(max_retries + 1).

### B4: Backoff sleep not awaited

1. **Nudge:** The two b02 requests are less than 0.3 s apart. Did the client wait at all?
2. **Area:** Run the tests and read the warnings. Then look at the sleep in send_with_retries.
3. **Exact:** Write `await asyncio.sleep(...)`.

### B5: Embeddings matched by position

1. **Nudge:** sup-01 and sup-04 have each other's norms. What is special about batch b03?
2. **Area:** Look at how _outcome assigns each response item to a document.
3. **Exact:** Use doc = batch['docs'][item['index']] instead of zipping by position.

### B6: tokens_per_doc floor-divided

1. **Nudge:** tokens_per_doc is a whole number. Should it be?
2. **Area:** Look at how summarize computes it.
3. **Exact:** Use / instead of //.

## "Why did that fix work?" probes

**B1**
- Why does json.dumps need a default hook at all here?
- What would happen if newest_update were a date instead of a datetime?

**B2**
- Why didn't any result change when the cap was missing?
- Why must the semaphore wrap the whole retry loop, not just one attempt?

**B3**
- Why did b02 and b06 still succeed with one attempt fewer?
- With the short loop, what does the last iteration do after b04's final 503?

**B4**
- Why didn't the missing wait change the number of attempts or the final status?
- Why is time.sleep() the wrong fix inside a coroutine?

**B5**
- Why did sup-03 come out right anyway?
- Why didn't the summary change?

**B6**
- Why does round(…, 2) not save you here?
- Which input would make the two versions agree?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `embedclient/retry.py` → `retry_delay`: Header names are lower-cased before the lookup, so 'Retry-After' is found whatever the case; float() accepts the fractional '0.3'; and backoff_s * 2 ** attempt with attempt starting at 0 is exactly the README formula (0.05, then 0.1).
- `embedclient/transport.py` → `send_sync`: urlopen raises HTTPError for 4xx/5xx; catching it and returning a Response with err.code keeps the status for the retry logic instead of turning it into an exception.
