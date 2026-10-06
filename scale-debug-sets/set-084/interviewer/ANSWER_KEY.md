# set-084 answer key: Async batch embedding client: jobs, polling, paged results

**Domain:** endpoint_client  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_requests.TestRequests.test_concurrency_cap` | B1 Fresh semaphore per batch |
| `test_2_jobs.TestJobLifecycle.test_rate_limit_honours_retry_after` | B2 Transient handler shadows RateLimited |
| `test_2_jobs.TestJobLifecycle.test_transient_errors_retried` | B3 max_attempts excludes the first try |
| `test_2_jobs.TestJobLifecycle.test_polls_wait_between_checks` | B4 Poll pause never awaited |
| `test_3_report.TestReport.test_failed_batch_reported` | B5 Failed batches dropped after gather |
| `test_3_report.TestReport.test_faq_embeddings` | B6 Next page read from the echoed token |

## Failing pattern with all bugs present

- `tests.test_1_requests.TestRequests.test_concurrency_cap`
- `tests.test_2_jobs.TestJobLifecycle.test_polls_wait_between_checks`
- `tests.test_2_jobs.TestJobLifecycle.test_rate_limit_honours_retry_after`
- `tests.test_2_jobs.TestJobLifecycle.test_transient_errors_retried`
- `tests.test_3_report.TestReport.test_failed_batch_reported`
- `tests.test_3_report.TestReport.test_faq_embeddings`

## Bugs (recommended order)

### B1: Fresh semaphore per batch

- **Type:** semaphore-unused
- **Symptom:** Test 1 test_concurrency_cap: '6 not less than or equal to 2'. All six batches hit the server at once. Every result is still correct.
- **Location:** `embedjobs/runner.py` → `run_batches`
- **Why it fails:** Each batch acquires its own brand-new semaphore, so nothing is shared and every batch starts at once. The shared `sem` built above is never used.
- **Failing test:** `test_1_requests.TestRequests.test_concurrency_cap`
- **Unblocks:** test_1 test_concurrency_cap.

Fix:

```diff
-        async with asyncio.Semaphore(client.config.max_concurrency):
+        async with sem:
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_concurrency_cap`):

```
AssertionError: 6 not less than or equal to 2
```

### B2: Transient handler shadows RateLimited

- **Type:** exception-order
- **Symptom:** Test 2 test_rate_limit_honours_retry_after: legal/1's wait is [['legal/1', 'retry', 0.05]] instead of 0.12. It still makes 2 creates and succeeds.
- **Location:** `embedjobs/retry.py` → `create_with_retries`
- **Why it fails:** RateLimited subclasses TransientError, and except clauses are tried top to bottom. With the parent first, a 429 is handled as a plain transient error and the server's 120 ms request is replaced by the 50 ms backoff. The RateLimited clause can never run.
- **Failing test:** `test_2_jobs.TestJobLifecycle.test_rate_limit_honours_retry_after`
- **Unblocks:** test_2 test_rate_limit_honours_retry_after.

Fix:

```diff
+        except RateLimited as err:
+            delay = err.retry_after_s if err.retry_after_s is not None else client.config.backoff_s * 2 ** attempt
         except TransientError:
             delay = client.config.backoff_s * 2 ** attempt
-        except RateLimited as err:
-            delay = err.retry_after_s if err.retry_after_s is not None else client.config.backoff_s * 2 ** attempt
```

Observed with only this bug applied (`tests.test_2_jobs.TestJobLifecycle.test_rate_limit_honours_retry_after`):

```
AssertionError: Lists differ: [['legal/1', 'retry', 0.05]] != [['legal/1', 'retry', 0.12]]

First differing element 0:
['legal/1', 'retry', 0.05]
['legal/1', 'retry', 0.12]

- [['legal/1', 'retry', 0.05]]
?                         ^^

+ [['legal/1', 'retry', 0.12]]
?                         ^^
```

### B3: max_attempts excludes the first try

- **Type:** retry-off-by-one
- **Symptom:** Test 2 test_transient_errors_retried: '2 != 3' create requests for product. product/1 then shows up in failures as retries_exhausted and pr-01/pr-02 are missing.
- **Location:** `embedjobs/config.py` → `Config.max_attempts`
- **Why it fails:** max_retries counts retries, not attempts. With max_retries = 2 the batch needs three create requests, but only two are made, so product/1 gives up after the 500 and the 503.
- **Failing test:** `test_2_jobs.TestJobLifecycle.test_transient_errors_retried`
- **Unblocks:** test_2 test_transient_errors_retried.

Fix:

```diff
-        return self.max_retries
+        return self.max_retries + 1
```

Observed with only this bug applied (`tests.test_2_jobs.TestJobLifecycle.test_transient_errors_retried`):

```
AssertionError: 2 != 3
```

### B4: Poll pause never awaited

- **Type:** missing-await
- **Symptom:** Test 2 test_polls_wait_between_checks: no poll waits recorded for news/1 ([] instead of three 0.01 waits), although it was still polled 4 times. A 'coroutine ... was never awaited' RuntimeWarning is printed.
- **Location:** `embedjobs/client.py` → `BatchClient.wait_until_done`
- **Why it fails:** Calling an async function without await only creates a coroutine object; its body (recording the wait and sleeping) never runs. The client then polls back to back. Python's 'coroutine was never awaited' RuntimeWarning is the tell.
- **Failing test:** `test_2_jobs.TestJobLifecycle.test_polls_wait_between_checks`
- **Unblocks:** test_2 test_polls_wait_between_checks.

Fix:

```diff
-            self.pause(label, "poll", self.config.poll_interval_s)
+            await self.pause(label, "poll", self.config.poll_interval_s)
```

Observed with only this bug applied (`tests.test_2_jobs.TestJobLifecycle.test_polls_wait_between_checks`):

```
AssertionError: Lists differ: [] != [['news/1', 'poll', 0.01], ['news/1', 'poll', 0.01], ['news/1', 'poll', 0.01]]

Second list contains 3 additional elements.
First extra element 0:
['news/1', 'poll', 0.01]

- []
+ [['news/1', 'poll', 0.01], ['news/1', 'poll', 0.01], ['news/1', 'poll', 0.01]]
```

### B5: Failed batches dropped after gather

- **Type:** gather-hides-failures
- **Symptom:** Test 3 test_failed_batch_reported: failures.get('support/1') is None instead of 'input_too_long'. failures is empty.
- **Location:** `embedjobs/runner.py` → `run_batches`
- **Why it fails:** With return_exceptions=True, gather hands exceptions back as values. Only the successes are used, so support/1's JobFailed disappears: its documents are missing and nothing says why.
- **Failing test:** `test_3_report.TestReport.test_failed_batch_reported`
- **Unblocks:** test_3 test_failed_batch_reported.

Fix:

```diff
-        if not isinstance(outcome, Exception):
+        if isinstance(outcome, Exception):
+            failures[batch.label] = getattr(outcome, "reason", type(outcome).__name__)
+        else:
             embedded.update(outcome)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_failed_batch_reported`):

```
AssertionError: None != 'input_too_long'
```

### B6: Next page read from the echoed token

- **Type:** pagination-cursor
- **Symptom:** Test 3 test_faq_embeddings: faq-06 is missing from the FAQ norms; the other six match.
- **Location:** `embedjobs/client.py` → `BatchClient.results`
- **Why it fails:** The server echoes the token that was sent as `page_token` (null on the first page) and puts the next one in `next_page_token`. Reading the echo stops after page one, so faq/1 (6 docs, page size 5) loses faq-06.
- **Failing test:** `test_3_report.TestReport.test_faq_embeddings`
- **Unblocks:** test_3 test_faq_embeddings.

Fix:

```diff
-            token = response.body.get("page_token")
+            token = response.body.get("next_page_token")
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_faq_embeddings`):

```
AssertionError: {'faq[63 chars]9.6954, 'faq-05': 12.4499, 'faq-07': 11.619} != {'faq[63 chars]9.6954, 'faq-05': 12.4499, 'faq-06': 15.0997, 'faq-07': 11.619}
  {'faq-01': 12.8841,
   'faq-02': 11.9583,
   'faq-03': 12.6095,
   'faq-04': 9.6954,
   'faq-05': 12.4499,
+  'faq-06': 15.0997,
   'faq-07': 11.619}
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `embedjobs/transport.py` → `send`: Catching HTTPError and returning a Response looks like it hides errors, but it is deliberate: status handling happens in raise_for_status, and HTTPError (a URLError subclass) is the only exception that carries a status and body.
- `embedjobs/errors.py` → `retry_after_seconds`: The header is in seconds and the body field in milliseconds, so only the body value is divided by 1000. `is not None` keeps a legitimate 0 ms.
