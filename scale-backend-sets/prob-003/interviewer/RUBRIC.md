# prob-003 rubric — Idempotent Task Intake with Tenant Rate Limits

Score each category 1–4. **4** = strong hire signal, **3** = hire, **2** = lean no, **1** = no.
Descriptions of 3 and 1 interpolate between the two given. Write down evidence, not impressions.

| Category | 4 looks like (this problem) | 2 looks like (this problem) |
|---|---|---|
| **Correct execution** | Parts 1 and 2 pass the hidden tests, including the `X-RateLimit-Remaining` change; Part 3 passes or nearly does. Without prompting: strict priority validation, canonical body comparison, per-tenant key scoping, 404 (not 403) for another tenant's task, replay before rate limit, `ceil` for `Retry-After`. | Happy-path create and replay work, but a raw-bytes comparison makes reordered bodies 409, replays spend tokens or get 429, `Retry-After` is `0` or rounded down, and the `tiny` plan fails because plan numbers are hard-coded. |
| **Debugging & unblocking** | Notices from a test, not a hint, that FastAPI returns 422 before the handler runs, and fixes the check order (dependency or manual `model_validate_json`). When the concurrency test shows 2 tasks, explains the race before writing the fix. | Needs hint 2 to understand why the missing-header case is 422; adds `time.sleep` to "fix" the concurrency test; keeps re-running a flaky test hoping it passes. |
| **Systematic thinking** | Writes the five-step order of checks as the skeleton of the handler; separates the bucket (`try_acquire` / `remaining` returning a decision), the idempotency store and the routes, so the mid-part change takes a few minutes and Part 3 swaps the store without touching the handler. | One long handler with dict lookups, bucket arithmetic and response building interleaved; the change needs edits in several branches; persistence is bolted on by dumping the whole in-memory dict to one file after each request. |
| **Production quality** | Injected clock everywhere; atomic persistence (sqlite transaction or temp file + `os.replace`), with task and record written together; one lock (or a DB unique constraint) around check → acquire → create; config validated at startup; clear `detail` messages; no ids or keys used unvalidated in file paths. | `time.time()` in the bucket; `open(path, "w")` in place; a lock only around the dict write (not the read); the key used directly as a file name with no validation; bare `except:` returning 500s. |
| **Testing** | Tests written alongside the code: parametrized validation table, replay/409/scoping tests, bucket tests that move `FakeClock` with exact refill values (0.25 s steps), a restart test with two `create_app` calls on one directory, a threaded test with a barrier. | Only manual curl checks or one happy-path test; rate-limit tests use real `sleep`; no restart or concurrency test. |
| **End-to-end ownership** | Runs `uvicorn` and replays a few lines of `sample_requests.jsonl` with curl (including a malformed body and a 429); finishes with a summary of what's done, what isn't (e.g. buckets reset on restart, no purge of expired records), and what they'd do next. | Stops at passing unit tests and never runs the server; leaves expiry or the restart path unfinished without saying so. |
| **Communication** | States the trade-offs: in-process lock vs DB constraint, buckets not persisted, global lock vs per-key locks, crash window between task and record. Asks one or two sharp questions (e.g. "is the TTL from creation or last use?") and finds the answer in the spec. | Silent for long stretches, or asks questions the spec answers (check order, rounding); can't explain why a replay shouldn't cost a token. |

## Hidden-test mapping

| Test file | Covers |
|---|---|
| `test_part1.py` | 201 shape and `created_at` from the clock, unique ids, 400/403 tenant header on all three endpoints, key format (400) incl. 64/65 chars, 17 invalid bodies (422, strict priority, extra fields), check order, replay body + header, canonical "same body", 409 on each field change, per-tenant key scope, 4xx not recorded, no-key never dedupes, GET owner-only 404, list order and isolation |
| `test_part2.py` | bucket starts full for 3 plans (incl. unseen `tiny`), `Retry-After` 1/4/3/2/1 rounding up, continuous refill, cap at burst, tenant isolation, replays free and served when empty, 400/409/422 free, 429 not recorded and creates nothing, GETs unlimited; `change`: `X-RateLimit-Remaining` countdown, floor after refill, on replays and 429s, pro plan |
| `test_part3.py` | restart: GET/list/order, replay + 409, new tasks after restart, separate storage dir; 10 concurrent same-key requests → one task, one original, rest replay/409; 10 distinct keys; burst 5 under 10 concurrent → exactly 5×201 + 5×429; expiry at exactly 24 h, different body after expiry, TTL from creation not last use, expiry across restart |

Use hidden-test results as evidence for **Correct execution** only; the other
categories come from watching the candidate work.
