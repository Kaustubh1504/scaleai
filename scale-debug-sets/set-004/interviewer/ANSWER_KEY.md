# set-004 answer key: LLM judge client: retries, parsing, paginated usage

**Domain:** endpoint_client  |  **Length:** FULL  |  **Difficulty:** easy

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_requests.TestRequests.test_attempts_per_request`
- `tests.test_1_requests.TestRequests.test_request_body`
- `tests.test_2_results.TestResults.test_results`
- `tests.test_2_results.TestResults.test_statuses`
- `tests.test_3_report.TestReport.test_counts`
- `tests.test_3_report.TestReport.test_latency`
- `tests.test_3_report.TestReport.test_scores`
- `tests.test_3_report.TestReport.test_usage_totals`

## Bugs (recommended order)

### B1: temperature 0 replaced by the default

- **Type:** falsy-zero
- **Symptom:** Test 1 test_request_body: the request has "temperature": 0.7, but config.json says 0.
- **Location:** `evalclient/config.py` → `load_config`
- **Why it fails:** `raw.get('temperature') or DEFAULT` treats the configured 0 as missing, because 0 is falsy. The spec says defaults only apply when a key is absent.
- **Unblocks:** Test 1 request body.

Fix:

```diff
-        temperature=float(raw.get("temperature") or DEFAULT_TEMPERATURE),
+        temperature=float(raw.get("temperature", DEFAULT_TEMPERATURE)),
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_request_body`):

```
AssertionError: {'mod[236 chars]s': 200, 'temperature': 0.7, 'metadata': {'request_id': 'r02'}} != {'mod[236 chars]s': 200, 'temperature': 0, 'metadata': {'request_id': 'r02'}}
  {'max_tokens': 200,
   'messages': [{'content': 'You are a strict grader. Reply with a JSON object '
                            'containing score (0-10) and passed.',
                 'role': 'system'},
                { ...
```

### B2: One attempt short of max_retries + 1

- **Type:** retry-off-by-one
- **Symptom:** Test 1: r03 and r07 get 3 attempts instead of 4. Test 2: r03 becomes http_error 429, although its 4th attempt would have succeeded. Test 3: counts become ok 6 / http_error 3, and total_tokens drops to 2538.
- **Location:** `evalclient/retry.py` → `send_with_retries`
- **Why it fails:** max_retries counts retries, not attempts. The first try plus 3 retries is 4 attempts, so the loop has to run max_retries + 1 times.
- **Unblocks:** Test 1 attempt counts, and r03 in Test 2. This exposes B4.

Fix:

```diff
-    for attempt in range(policy.max_retries):
+    for attempt in range(policy.max_retries + 1):
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_attempts_per_request`):

```
AssertionError: {'r02': 1, 'r03': 3, 'r07': 3, 'r01': 1, 'r05': 1, 'r09': 1[36 chars]': 2} != {'r02': 1, 'r03': 4, 'r07': 4, 'r01': 1, 'r05': 1, 'r09': 1[36 chars]': 2}
  {'r01': 1,
   'r02': 1,
-  'r03': 3,
?         ^

+  'r03': 4,
?         ^

   'r04': 2,
   'r05': 1,
   'r06': 1,
-  'r07': 3,
?         ^

+  'r07': 4,
?         ^

   'r08': 1,
   'r09': 1,
   'r10': 2}
```

### B3: 4xx responses treated as success

- **Type:** ignoring-http-status
- **Symptom:** Test 2: r05 shows parse_error with http_status 400. It should be http_error. Test 3 counts: parse_error 2, http_error 1.
- **Location:** `evalclient/client.py` → `ModelClient.grade`
- **Why it fails:** Only 5xx counts as an error, so a 400 body ({"error": ...}) gets passed to the verdict parser. The parser finds no choices and reports parse_error, which hides the real HTTP failure.
- **Unblocks:** Test 2 status for r05, and the Test 3 counts.

Fix:

```diff
-        if response.status >= 500:
+        if response.status >= 400:
```

Observed with only this bug applied (`tests.test_2_results.TestResults.test_results`):

```
AssertionError: {'r02': {'status': 'ok', 'http_status': 200, [732 chars]rue}} != {'r01': {'status': 'ok', 'http_status': 200, [731 chars]rue}}
  {'r01': {'http_status': 200, 'passed': True, 'score': 8.0, 'status': 'ok'},
   'r02': {'http_status': 200, 'passed': False, 'score': 3.0, 'status': 'ok'},
   'r03': {'http_status': 200, 'passed': True, 'score': 6.0, 'status': 'ok'},
   'r04': {'http_statu ...
```

### B4: Verdict JSON cut at the first closing brace

- **Type:** slice-bounds
- **Symptom:** Only visible after B2 is fixed. r03 (the only verdict with a nested 'rubric' object) shows parse_error instead of ok 6.0/True. Test 3 counts and mean_score change.
- **Location:** `evalclient/parsing.py` → `extract_json`
- **Why it fails:** Slicing to the first '}' stops at the end of the nested object, which leaves invalid JSON, so json.loads fails. The outer object ends at the last '}'.
- **Unblocks:** Test 2 r03, and Test 3 counts and scores.
- **Masked:** invisible until B2 is fixed (identical test output either way).

Fix:

```diff
-    start, end = text.find("{"), text.find("}")
+    start, end = text.find("{"), text.rfind("}")
```

Observed with only this bug applied (`tests.test_2_results.TestResults.test_results`):

```
AssertionError: {'r02': {'status': 'ok', 'http_status': 200, [741 chars]rue}} != {'r01': {'status': 'ok', 'http_status': 200, [731 chars]rue}}
  {'r01': {'http_status': 200, 'passed': True, 'score': 8.0, 'status': 'ok'},
   'r02': {'http_status': 200, 'passed': False, 'score': 3.0, 'status': 'ok'},
+  'r03': {'http_status': 200, 'passed': True, 'score': 6.0, 'status': 'ok'},
-  'r03': {'http_statu ...
```

### B5: Last usage page dropped

- **Type:** pagination-cursor
- **Symptom:** Test 3 only: total_tokens is 2276 instead of 3039, and p50_latency_s is 0.963 instead of 0.9. All 3 pages are still requested (test_usage_fetched_page_by_page passes), but the last page's records are thrown away.
- **Location:** `evalclient/runner.py` → `collect_usage`
- **Why it fails:** The loop checks for the end before storing the page it just fetched. The final page has next_cursor null, so its data is never added.
- **Unblocks:** Test 3 total_tokens (and latency together with B6).
- **Masked:** only surfaces in test_3_report.

Fix:

```diff
+        items.extend(page["data"])
         cursor = page.get("next_cursor")
         if not cursor:
             break
-        items.extend(page["data"])
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_latency`):

```
AssertionError: 0.963 != 0.9
```

### B6: Median latency reported in milliseconds

- **Type:** ms-vs-s
- **Symptom:** Test 3 only: p50_latency_s is 900.0 instead of 0.9 (962.5 while B5 is also present).
- **Location:** `evalclient/reports.py` → `summarize`
- **Why it fails:** The usage records are in latency_ms, but the field is reported in seconds, and the code never divides by 1000.
- **Unblocks:** Test 3 latency.
- **Masked:** only surfaces in test_3_report.

Fix:

```diff
-        "p50_latency_s": round(statistics.median(latencies), 3) if latencies else None,
+        "p50_latency_s": round(statistics.median(latencies) / 1000, 3) if latencies else None,
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_latency`):

```
AssertionError: 900.0 != 0.9
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `evalclient/transport.py` → `send`: Catching urllib.error.HTTPError looks like swallowing errors. But urllib raises HTTPError for every 4xx/5xx response, and the exception is the response. Turning it into Response(status, headers, body) is what lets the retry and status logic see 429/503 at all.
