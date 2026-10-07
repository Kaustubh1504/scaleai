# set-100 answer key: Streaming eval relay: request ids, retries, policy gate, resent deltas, failures, baselines

**Domain:** endpoint_client  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_requests.TestRequests.test_1_request_ids_match_prompts` | B1 Shared header dict mutated per request |
| `test_1_requests.TestRequests.test_2_attempts_for_unavailable_prompt` | B2 Retry budget counted in attempts |
| `test_2_answers.TestAnswers.test_3_blocked_prompts` | B3 Policy check never awaited |
| `test_2_answers.TestAnswers.test_4_resent_delta` | B4 Resent delta joined twice |
| `test_3_report.TestReport.test_5_failed_prompts` | B5 Failed prompts dropped after gather |
| `test_3_report.TestReport.test_6_regressions` | B6 Cursor taken from the echo field |

## Failing pattern with all bugs present

- `tests.test_1_requests.TestRequests.test_1_request_ids_match_prompts`
- `tests.test_1_requests.TestRequests.test_2_attempts_for_unavailable_prompt`
- `tests.test_2_answers.TestAnswers.test_3_blocked_prompts`
- `tests.test_2_answers.TestAnswers.test_4_resent_delta`
- `tests.test_3_report.TestReport.test_5_failed_prompts`
- `tests.test_3_report.TestReport.test_6_regressions`

## Bugs (recommended order)

### B1: Shared header dict mutated per request

- **Type:** async-shared-state
- **Symptom:** Test 1 test_1_request_ids_match_prompts: the dicts differ, e.g. 'p02': ['p14-1'] and 'p13': ['p14-1'] instead of ['p02-1'] / ['p13-1'] (which ids collide varies with scheduling). Several requests reached the relay carrying another prompt's X-Request-Id. Answers, attempts and the report are all still correct.
- **Location:** `relaygrade/client.py` → `RelayClient.complete`
- **Why it fails:** Every concurrent request writes its id into the one `self.headers` dict, and `wire.send` only serialises the headers after `await asyncio.open_connection(...)`. While one task is connecting, the next task overwrites the id, so the request goes out with another prompt's X-Request-Id. Answers are unaffected because the relay routes by the body's prompt_id.
- **Failing test:** `test_1_requests.TestRequests.test_1_request_ids_match_prompts`
- **Unblocks:** test_1 test_1_request_ids_match_prompts.

Fix:

```diff
-        headers = self.headers
-        headers["X-Request-Id"] = f"{prompt.id}-{attempt}"
+        headers = {**self.headers, "X-Request-Id": f"{prompt.id}-{attempt}"}
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_1_request_ids_match_prompts`):

```
AssertionError: {'p01[19 chars]: ['p14-1'], 'p03': ['p03-2', 'p03-3', 'p06-1'[222 chars]-1']} != {'p01[19 chars]: ['p02-1'], 'p03': ['p03-1', 'p03-2', 'p03-3'[222 chars]-1']}
  {'p01': ['p01-1'],
-  'p02': ['p14-1'],
?            ^^

+  'p02': ['p02-1'],
?            ^^

-  'p03': ['p03-2', 'p03-3', 'p06-1'],
?                          ---------

+  'p03': ['p03-1', 'p03-2', 'p03-3'],
?          + ...
```

### B2: Retry budget counted in attempts

- **Type:** retry-off-by-one
- **Symptom:** Test 1 test_2_attempts_for_unavailable_prompt: '3 != 4'. The relay saw only 3 completion requests for p11. p11 is still failed with 'HTTP 503' and p03 still recovers on its third attempt.
- **Location:** `relaygrade/retry.py` → `with_retries`
- **Why it fails:** `retries` already counts retries made; adding one compares attempts against a retry budget, so the loop gives up one retry early (3 attempts instead of max_retries + 1 = 4). p03 still recovers on its third attempt, so only the always-503 prompt shows it.
- **Failing test:** `test_1_requests.TestRequests.test_2_attempts_for_unavailable_prompt`
- **Unblocks:** test_1 test_2_attempts_for_unavailable_prompt.

Fix:

```diff
-        if response.status not in RETRYABLE or retries + 1 >= policy.max_retries:
+        if response.status not in RETRYABLE or retries >= policy.max_retries:
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_2_attempts_for_unavailable_prompt`):

```
AssertionError: 3 != 4
```

### B3: Policy check never awaited

- **Type:** missing-await
- **Symptom:** Test 2 test_3_blocked_prompts: ['p04', 'p09', 'p12'] != ['p09'], plus a RuntimeWarning "coroutine 'RelayClient.policy_blocks' was never awaited". Every review prompt is blocked and no /v1/policy request reaches the relay.
- **Location:** `relaygrade/runner.py` → `Runner.run_one`
- **Why it fails:** Without `await`, `policy_blocks` returns a coroutine object, which is always truthy, so every review prompt is treated as blocked and the policy endpoint is never called (Python warns 'coroutine ... was never awaited').
- **Failing test:** `test_2_answers.TestAnswers.test_3_blocked_prompts`
- **Unblocks:** test_2 test_3_blocked_prompts.

Fix:

```diff
-        if prompt.review and self.client.policy_blocks(prompt.id):
+        if prompt.review and await self.client.policy_blocks(prompt.id):
```

Observed with only this bug applied (`tests.test_2_answers.TestAnswers.test_3_blocked_prompts`):

```
AssertionError: Lists differ: ['p04', 'p09', 'p12'] != ['p09']

First differing element 0:
'p04'
'p09'

First list contains 2 additional elements.
First extra element 1:
'p09'

- ['p04', 'p09', 'p12']
+ ['p09']
```

### B4: Resent delta joined twice

- **Type:** missing-dedupe
- **Symptom:** Test 2 test_4_resent_delta: 'Hamlet was written written by William Shakespeare.' != 'Hamlet was written by William Shakespeare.'. p06 still passes grading, so nothing else changes.
- **Location:** `relaygrade/stream.py` → `assemble`
- **Why it fails:** The relay resends seq 3 for p06. Without the `seen` check both copies are kept, and sorting by seq puts them side by side, so the answer repeats ' written'. The answer still contains 'Shakespeare', so grading hides it.
- **Failing test:** `test_2_answers.TestAnswers.test_4_resent_delta`
- **Unblocks:** test_2 test_4_resent_delta.

Fix:

```diff
+        if event["seq"] in seen:
+            continue
```

Observed with only this bug applied (`tests.test_2_answers.TestAnswers.test_4_resent_delta`):

```
AssertionError: 'Hamlet was written written by William Shakespeare.' != 'Hamlet was written by William Shakespeare.'
- Hamlet was written written by William Shakespeare.
?                    --------
+ Hamlet was written by William Shakespeare.
```

### B5: Failed prompts dropped after gather

- **Type:** gather-hides-failures
- **Symptom:** Test 3 test_5_failed_prompts: {} != {'p07': 'HTTP 400', 'p10': 'stream ended before done', 'p11': 'HTTP 503'}. The three prompts are missing from answers, blocked and failed alike.
- **Location:** `relaygrade/runner.py` → `Runner.run_all`
- **Why it fails:** `gather(..., return_exceptions=True)` hands the exceptions back as results; skipping them without recording means p07 (400), p10 (truncated stream) and p11 (503) vanish from the report instead of appearing under `failed`.
- **Failing test:** `test_3_report.TestReport.test_5_failed_prompts`
- **Unblocks:** test_3 test_5_failed_prompts.

Fix:

```diff
             if isinstance(outcome, Exception):
+                failed[prompt.id] = str(outcome)
                 continue
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_5_failed_prompts`):

```
AssertionError: {} != {'p07': 'HTTP 400', 'p10': 'stream ended before done', 'p11': 'HTTP 503'}
- {}
+ {'p07': 'HTTP 400', 'p10': 'stream ended before done', 'p11': 'HTTP 503'}
```

### B6: Cursor taken from the echo field

- **Type:** pagination-cursor
- **Symptom:** Test 3 test_6_regressions: ['p08'] != ['p05', 'p08', 'p13']. Only one /v1/baselines request is made, so p05 keeps its old r1 score 0 and p13 has no baseline.
- **Location:** `relaygrade/history.py` → `fetch_baselines`
- **Why it fails:** Each page echoes the cursor that was sent as `cursor` and gives the next one as `next_cursor`. The first page's echo is null, so the loop stops after five records: p05 keeps its old r1 score 0 and p13 has no baseline, leaving only p08 as a regression.
- **Failing test:** `test_3_report.TestReport.test_6_regressions`
- **Unblocks:** test_3 test_6_regressions.

Fix:

```diff
-        cursor = page.get("cursor")
+        cursor = page.get("next_cursor")
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_6_regressions`):

```
AssertionError: Lists differ: ['p08'] != ['p05', 'p08', 'p13']

First differing element 0:
'p08'
'p05'

Second list contains 2 additional elements.
First extra element 1:
'p08'

- ['p08']
+ ['p05', 'p08', 'p13']
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `relaygrade/wire.py` → `_read_chunked`: Each chunk is `<hex size>\r\n<data>\r\n`, so reading size + 2 bytes and dropping the last two removes exactly the chunk's trailing CRLF. The size is hex (base 16), chunk extensions after `;` are ignored, and the zero-size chunk is followed by one blank line, which is consumed before returning.
- `relaygrade/history.py` → `latest_baselines`: The baseline API returns records oldest run first, so letting a later record overwrite an earlier one keeps the most recent score, as the spec requires (p05: r1 score 0, then r2 score 1). Keeping the first record would pick the oldest run.
