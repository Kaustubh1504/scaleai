# set-100 interviewer notes

**Scenario:** An eval harness streams model answers from a mock completion relay over raw HTTP/1.1 (asyncio.open_connection, chunked NDJSON), gates review prompts through a policy endpoint, retries 429/5xx with Retry-After/backoff, rebuilds each answer from out-of-order and resent delta events, grades it, and pages through cursor-paginated baselines to flag regressions. Test 1 checks what the relay saw, test 2 the rebuilt answers, test 3 the report.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Shared header dict mutated per request

1. **Nudge:** The relay received request ids that belong to other prompts. Where is the header built, and when is it actually written to the socket?
2. **Area:** Look at RelayClient.complete: which dict does it put X-Request-Id into, and who else uses that dict?
3. **Exact:** Build a per-request copy: `headers = {**self.headers, "X-Request-Id": f"{prompt.id}-{attempt}"}`.

### B2: Retry budget counted in attempts

1. **Nudge:** How many attempts does the spec allow with max_retries = 3?
2. **Area:** Look at the stop condition in with_retries: what does `retries` count at that point?
3. **Exact:** Stop when `retries >= policy.max_retries`.

### B3: Policy check never awaited

1. **Nudge:** p04 and p12 are allowed by the policy service, yet they are blocked. Did the relay ever receive a policy request?
2. **Area:** Look at the review gate at the top of Runner.run_one, and at the RuntimeWarning in the test output.
3. **Exact:** `if prompt.review and await self.client.policy_blocks(prompt.id):`.

### B4: Resent delta joined twice

1. **Nudge:** Which word appears twice in p06's answer, and what does the mock relay deliver for p06?
2. **Area:** Look at how assemble uses `seen`.
3. **Exact:** Skip events whose seq is already in `seen` before appending.

### B5: Failed prompts dropped after gather

1. **Nudge:** Three prompts are neither answered, blocked nor failed. Where did they go?
2. **Area:** Look at what run_all does with exception outcomes from gather.
3. **Exact:** Record them: `failed[prompt.id] = str(outcome)` before `continue`.

### B6: Cursor taken from the echo field

1. **Nudge:** How many baseline requests did the relay receive, and how many records does it hold?
2. **Area:** Look at which response field fetch_baselines uses as the next cursor.
3. **Exact:** Use `page.get("next_cursor")`.

## "Why did that fix work?" probes

**B1**
- Why does the mix-up only happen with concurrency, and which await opens the window?
- Why do the policy and baseline requests also start carrying an X-Request-Id?

**B2**
- Why does p03, which also gets retried, still succeed?
- Why does the failure reason for p11 stay `HTTP 503` either way?

**B3**
- Why is a coroutine object truthy, and why was no policy request logged?
- Why are p04 and p12 not counted as regressions or failures when this happens?

**B4**
- Why does p02's out-of-order stream still come out right?
- Why does p06 still pass grading with the repeated word?

**B5**
- Why doesn't one failing prompt stop the others?
- What would change if return_exceptions were False?

**B6**
- Why does p05 drop out of the regressions as well as p13?
- Why is latest_baselines not the cause even though p05's score looks stale?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `relaygrade/wire.py` → `_read_chunked`: Each chunk is `<hex size>\r\n<data>\r\n`, so reading size + 2 bytes and dropping the last two removes exactly the chunk's trailing CRLF. The size is hex (base 16), chunk extensions after `;` are ignored, and the zero-size chunk is followed by one blank line, which is consumed before returning.
- `relaygrade/history.py` → `latest_baselines`: The baseline API returns records oldest run first, so letting a later record overwrite an earlier one keeps the most recent score, as the spec requires (p05: r1 score 0, then r2 score 1). Keeping the first record would pick the oldest run.
