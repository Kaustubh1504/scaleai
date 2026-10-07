# prob-008 rubric — Annotator Earnings Calculator

Score each category 1–4. **4** = strong hire signal, **3** = hire, **2** = lean no, **1** = no.
Write down evidence, not impressions.

| Category | 4 looks like (this problem) | 2 looks like (this problem) |
|---|---|---|
| **Correct execution** | Parts 1 and 2 pass on seed 83 including the gold bonus; Part 3 publishes exactly once per payable annotator under scripted faults. | Report right on clean data only; epoch-ms or unknown rewards break it; payouts duplicated after a lost response. |
| **Debugging & unblocking** | Compares their numbers against a hand-built case via `api.insert`; inspects `api.rendered(...)` to see the wire; reads `data/recorded/` when something parses oddly. | Tweaks parsing until the test passes; can't explain why totals differ by a few cents; needs hint 2 to find the pagination envelopes. |
| **Systematic thinking** | Lists the intern's defects up front; separates fetch → normalize → compute → publish; one table drives pagination; one normalizer per rule. | Fixes defects one by one as tests fail; normalization scattered through the calculation; pagination code duplicated per collection. |
| **Production quality** | Integer cents throughout; unknown wire forms raise with the record id (never silently 0); idempotency key stable per (period, annotator); atomic CSV; injected clock; bounded retries. | Floats for money; `except: return 0`; idempotency key includes a timestamp; `time.sleep`; retries forever on 429. |
| **Testing** | Updates the intern's tests deliberately; unit tests per normalization rule and the verdict tie-break; integration tests on the mock with inserted records; payout tests with scripted `malformed`/503 asserting `api.canonical("results")`. | Keeps the old tests failing or deletes them; one end-to-end test with a seed's exact total. |
| **End-to-end ownership** | Runs the CLI against the server, opens the CSV, checks totals reconcile with the report; explains what finance must resolve by hand (unknown rewards, on-hold). | Never runs the CLI; leaves `--publish` unwired; doesn't mention unknown rewards to "finance". |
| **Communication** | Talks about money correctness and who rounding favours; flags the "amount changed between runs" hole in idempotency unprompted or when asked. | Can't explain why `int(usd * 100)` is wrong; treats "it ran" as "it's correct". |

## Hidden-test mapping

| Test file | Covers |
|---|---|
| `test_part1.py` | oracle match on seed 83 (clean API), every page of every collection, latest review + half-open period, sorting and integer cents, totals and period, `ApiError` status+path, `AuthError`, gold bonus (`change`) |
| `test_part2.py` | oracle match on the messy API, every wire variant, verdict rule across mixed timestamp formats, unknown rewards excluded and listed, on-hold rows and `payable_cents`, clean data still works |
| `test_part3.py` | one payout per payable annotator, on-hold/zero not posted, re-run creates nothing, lost response not paid twice, failure isolation, 4xx not retried, backoff ranges, 4-attempt cap, Retry-After, 429s don't use attempts, 10×429 gives up, timeout/malformed transient, 10 s timeout, token endpoint retried, real rate limit, bad secret |
