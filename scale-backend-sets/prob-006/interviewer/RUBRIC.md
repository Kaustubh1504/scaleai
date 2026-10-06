# prob-006 rubric — Project Throughput Report

Score each category 1–4. **4** = strong hire signal, **3** = hire, **2** = lean no, **1** = no.
Write down evidence, not impressions.

| Category | 4 looks like (this problem) | 2 looks like (this problem) |
|---|---|---|
| **Correct execution** | All Part 1 and 2 hidden tests pass, including the mid-part change. Part 3 passes or nearly does: both Retry-After forms, the 4-attempt cap, the 10 s timeout. | Report works on the default seed but is wrong on another (an off-by-one page loop, a hard-coded detail); token refresh only works when nothing is revoked. |
| **Debugging & unblocking** | Reproduces failures on purpose with `FaultConfig(scripted=...)` and `api.log`; when a test hangs or loops, inspects the log or the clock instead of guessing. | Adds prints everywhere; needs hints to see that the HTTP-date wait must use the `Date` header, or why the 8 s test times out. |
| **Systematic thinking** | Has one request path (`_send`) that owns auth, retries and parsing; pagination as generators; computation separate from I/O. The mid-part change is a few lines in the summarize function. | Retry and token logic copy-pasted into each fetch function; aggregation interleaved with HTTP calls; each new requirement patched in a different place. |
| **Production quality** | Uses the injected clock everywhere; clear exception types carrying status and path; no infinite loops (caps on 401 and 429); timeouts on every call; atomic output file; no secrets in logs. | `time.sleep`/`time.time`; bare `except Exception: retry`; unbounded `while True` on 429; JSON decode errors crash the job. |
| **Testing** | Tests per behaviour using the mock: pagination boundaries, expiry with `FakeClock` + latency, revocation, scripted 503/429/timeout/malformed, and assertions on `clock.sleeps` and `api.log`. | One test that the report "has projects"; nothing exercises failure paths; tests depend on one seed's exact numbers. |
| **End-to-end ownership** | Reads `API.md` and the recorded responses before coding; runs the CLI against the real mock server; reports what is done, what is untested and what they'd do next. | Never runs the CLI; never looks at a real response; stops when unit tests pass. |
| **Communication** | Explains the retry policy and why 401 and 429 are special; asks sharp questions (e.g. "is a revoked token expected?") and checks the docs for the answer. | Can't explain the difference between a transient error and a 4xx; asks questions answered in API.md. |

## Hidden-test mapping

| Test file | Covers |
|---|---|
| `test_part1.py` | oracle match (seed 61), totals, `generated_at`, multi-page crawl (3 project pages, cursor pages), null rates, `ApiError` status+path, `AuthError` on bad credentials, `tasks_by_status` (`change`) |
| `test_part2.py` | customer rollup, proactive refresh (no 401s with a 10 s TTL and 1 s latency), refresh-token grant, fallback when refresh fails, one 401 retry, second 401 → `AuthError` |
| `test_part3.py` | 5xx backoff ranges and jitter, 4-attempt cap, token endpoint retried, malformed + timeout transient, 10 s timeout, Retry-After seconds exact, HTTP-date under a real limit, 429s don't use attempts, 10×429 gives up, each page once with max page sizes |
