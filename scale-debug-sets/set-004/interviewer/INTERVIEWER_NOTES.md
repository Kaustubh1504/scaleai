# set-004 interviewer notes

**Scenario:** Batch client for a judge-model HTTP endpoint (local mock server). It builds chat requests from config, retries 429/5xx, parses fenced or nested JSON verdicts, then pages through usage records to build a summary.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: temperature 0 replaced by the default

1. **Nudge:** Compare the body the server received with config.json, field by field.
2. **Area:** Look at how config.py applies its defaults.
3. **Exact:** Use raw.get("temperature", DEFAULT_TEMPERATURE) instead of `or`.

### B2: One attempt short of max_retries + 1

1. **Nudge:** How many times did the server see r03? How many does the README allow?
2. **Area:** Look at the loop bound in retry.py.
3. **Exact:** Use range(policy.max_retries + 1).

### B3: 4xx responses treated as success

1. **Nudge:** r05 got HTTP 400. Why does its result say parse_error?
2. **Area:** Look at how grade() decides that a response failed.
3. **Exact:** The final-status check should be response.status >= 400.

### B4: Verdict JSON cut at the first closing brace

1. **Nudge:** Look at r03's raw content in tests/mock_server.py. How is it different from the others?
2. **Area:** Look at how extract_json finds where the object ends.
3. **Exact:** Use text.rfind("}") for the end of the slice.

### B5: Last usage page dropped

1. **Nudge:** Three usage pages were fetched. How many records ended up being summed?
2. **Area:** Walk through collect_usage on the final page.
3. **Exact:** Move items.extend(page["data"]) above the next_cursor check.

### B6: Median latency reported in milliseconds

1. **Nudge:** Look at the units in the field name and in the usage records.
2. **Area:** Look at the p50 computation in reports.py.
3. **Exact:** Divide the median by 1000 before rounding.

## "Why did that fix work?" probes

**B1**
- Which other config keys would break the same way if someone wrote them with `or`?
- Why doesn't anything in Tests 2 or 3 notice the wrong temperature?

**B2**
- With the fix, why doesn't the code sleep after the very last failed attempt?
- If max_retries were 0, how many requests should go out, before and after your fix?

**B3**
- Why didn't parse_completion crash on an error body?
- Would checking `response.status != 200` be equivalent here? What about 204 or 201?

**B4**
- Why couldn't you see this before the retry fix?
- rfind would still break if prose after the JSON contained a '}'. How would you make extraction robust (e.g. json.JSONDecoder.raw_decode)?

**B5**
- What would happen if the server returned an empty final page with a null cursor?
- How would you write a test that catches this with only a single page of data?

**B6**
- Why should you divide before rounding and not after?
- Where would you put a unit conversion so a mistake like this can't happen twice?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `evalclient/transport.py` → `send`: Catching urllib.error.HTTPError looks like swallowing errors. But urllib raises HTTPError for every 4xx/5xx response, and the exception is the response. Turning it into Response(status, headers, body) is what lets the retry and status logic see 429/503 at all.
