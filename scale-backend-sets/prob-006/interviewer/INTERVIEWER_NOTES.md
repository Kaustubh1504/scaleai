# prob-006 — Project Throughput Report (interviewer notes)

**Kind:** api-client. The candidate is handed a third-party API (`API.md`) and
must query it to compute a report. This matches the current format of the round:
query, paginate, authenticate, handle errors and rate limits, compute an answer.
**Difficulty:** medium · **Mode:** plain Python (library + CLI) · **Starter:** skeleton · **Planted bugs:** none

## Setup

```bash
python tools/export_candidate.py prob-006 ~/interview --part1-only
# afterwards, from scale-backend-sets/:
SOLUTION_DIR=~/interview/prob-006 python -m pytest prob-006/interviewer/hidden_tests -q
SOLUTION_DIR=... python -m pytest prob-006/interviewer/hidden_tests/test_part1.py -m "not change"
```

The hidden tests build the API from `shared/` with **seed 61** and different
credentials (`hidden-id` / `hidden-secret`). Expected values come from an oracle in
`hidden_tests/conftest.py` over the canonical data, so hard-coded numbers or
credentials fail. They call `ApiClient(http, client_id, client_secret, clock)`
and `build_report(client)`. If the candidate changed those signatures, adapt the
call in a scratch copy rather than failing them.

The candidate can also run the API for real
(`python -m mock_services.api_server`) and the CLI against it.

## Timeline

### 60-minute mode

| min | what happens |
|---|---|
| 0–5 | Hand over `PART1.md`. Candidate reads `API.md`, `data/recorded/`, `mock_services/api.py`. A strong candidate makes one request by hand first (the smoke test shows how). |
| 5–15 | Token, `get()`, page-number loop for projects, cursor loop for tasks. |
| ~12 | **Drop the mid-part change** (below), once projects are listed. |
| 15–22 | Aggregation (rates, medians, totals), tests. Reveal `PART2.md`. |
| 22–38 | Part 2: expiry by clock with a 5 s margin, refresh grant + fallback, single 401 retry, customer rollup, tests with `token_ttl_s=10, latency_s=1.0`. |
| 38–55 | Part 3: retry loop (transient set, jittered backoff), 429 with both Retry-After forms, timeout=10, page sizes. |
| 55–60 | Follow-up discussion. |

If behind at minute 25, reveal Part 2 anyway. If behind at minute 45, take the
retry loop only and discuss 429 handling.

### 30-minute mode (Part 1 plus the start of Part 2)

| min | what happens |
|---|---|
| 0–3 | `PART1.md`, read `API.md`. |
| 3–18 | Auth, both pagination loops, the report. Skip the mid-part change unless done by minute 14. |
| 18–20 | Reveal `PART2.md`. |
| 20–27 | Proactive expiry check + one 401 retry, ideally with a FakeClock test. |
| 27–30 | Follow-up #1. |

Run `test_part1.py -m "not change"` and `test_part2.py`; score Part 3 categories "not observed".

## Mid-part requirement change (Part 1, ~minute 12)

Say, verbatim:

> "Ops also wants a breakdown: add `tasks_by_status` to each project row: a
> dict with the count of tasks in each status. Always include all four keys
> (`pending`, `in_progress`, `completed`, `rejected`), even when the count is 0."

It is additive, so base tests pass with or without it. It tests whether the
aggregation is a clean function of `(project, tasks)` rather than counters
scattered through the fetch loop. Hidden test: `test_part1.py::test_tasks_by_status` (`change`).

## Planted bugs

None.

## Hint ladder

**Part 1**
1. "Make one request by hand in a REPL first. What does the envelope look like for projects vs tasks?"
2. "The two endpoints paginate differently. What tells you to stop in each case?" (`total_pages` vs `next_cursor is None`)
3. "Separate fetching (`iter_projects`, `iter_project_tasks`) from computing (`summarize(project, tasks)`)."

**Part 2**
1. "When does your token expire, by whose clock?" (issue time + `expires_in`, on the injected clock)
2. "What happens if the token is revoked between two pages?" → 401 path.
3. "Put the auth logic in one place, the function that sends requests, not in each caller."

**Part 3**
1. "List the failure types from API.md. Which are safe to retry?"
2. "How do you compute the wait from an HTTP-date `Retry-After`?" (`email.utils.parsedate_to_datetime`, minus `Date`)
3. "Write the retry loop around a single request, then make everything use it."

## Common pitfalls (what the hidden tests catch)

* Stopping the cursor loop on a short page instead of on `next_cursor is None`, or the page loop one page early/late.
* Hard-coding `client`/`secret` or seed-6 numbers (hidden tests use other credentials and seed 61).
* Token expiry computed with `time.time()` instead of the injected clock (Part 2 tests never trigger refresh).
* Refreshing on every request (works but wasteful), or never using the refresh-token grant.
* Retrying a 401 forever, or not at all.
* Treating 429 like a 5xx (jittered backoff instead of Retry-After) or letting 429s consume the 4 attempts.
* Parsing HTTP-date `Retry-After` against the local clock instead of the `Date` header.
* Not passing `timeout=10`: httpx defaults to 5 s, and the 8 s-latency test times out.
* Calling `.json()` without guarding against a truncated 200 body.
* Using the API's default page sizes (more requests than necessary).

## Follow-up questions

**1. "We now have 10,000 projects and a limit of 10 requests/second. How long does the report take, and how would you make it faster?"**
Strong: estimate first (pages ≈ projects × ceil(tasks/25); at 10 rps that's the floor);
concurrency only helps up to the rate limit, so use a shared token bucket across
workers and respect `X-RateLimit-Remaining`/`Reset` proactively rather than
discovering 429s; a bounded worker pool; prefer bulk endpoints or filters
(`?status=completed`) when they reduce pages; ask the provider for a higher limit or an export.

**2. "Tasks are being completed while you crawl. Is the report consistent?"**
Strong: cursor (keyset) pagination doesn't skip or duplicate on inserts, but page
numbers do; the report is a "rolling" snapshot, not point-in-time; options include
`updated_since` to re-read changes made during the crawl, recording the crawl start
and end, or asking for a snapshot/export endpoint. Explain how they would detect duplicates (task id).

**3. "Make the nightly job incremental."**
Strong: persist the previous report + a high-water mark (`max(updated_at)` seen,
minus a safety window for clock skew); next run fetches only `updated_since`; merge
by id; periodic full refresh to catch deletes (which incremental sync misses);
idempotent writes, atomic output.

## Reference solution

`reference/report/client.py`: one `_send()` with the retry policy (transient set,
equal-jitter backoff, separate 429 counter, Retry-After parsing for both forms);
token handling in `_ensure_token()`/`_fetch_token()` (5 s margin, refresh grant with
fallback); `get()` adds the single 401 retry; generators for both pagination styles.
`report.py` is pure computation over fetched records; `__main__.py` writes atomically.

Lines a candidate must add: Part 1 ≈ 75, Part 2 ≈ 45, Part 3 ≈ 50 (172 total).
