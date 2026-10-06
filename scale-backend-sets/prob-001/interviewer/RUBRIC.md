# prob-001 rubric — Support Ticket Ingestion & LLM Triage

Score each category 1–4. **4** = strong hire signal, **3** = hire, **2** = lean no, **1** = no.
Descriptions of 3 and 1 interpolate between the two given. Write down evidence, not impressions.

| Category | 4 looks like (this problem) | 2 looks like (this problem) |
|---|---|---|
| **Correct execution** | Parts 1 and 2 fully pass hidden tests, the JSONL change is in, and Part 3 passes or nearly does. Row numbers, rule order, duplicate-of-valid-only and fenced JSON are handled without prompting. | CSV happy path works but several edge rows are misreported (off-by-one rows, short rows crash with `NoneType.strip`); classification works only on clean model output. |
| **Debugging & unblocking** | When a test fails, reads the traceback, prints `resp.text` from the mock, forms a hypothesis and fixes it fast. Uses the mock's `fault_script` / `prompt_faults` to reproduce a failure on purpose. | Changes code at random until it passes; needs hint 2+ to discover what the mock actually returns; stuck >5 min on the multipart upload or on `csv` quoting. |
| **Systematic thinking** | Separates parse → validate → persist; adds JSONL in minutes because validation takes a record dict. Retry logic is one per-ticket function with clear retryable / non-retryable / invalid-output branches. | One long endpoint function that mixes csv parsing, validation and the response; JSONL is a copy-pasted second endpoint body; retries are nested try/excepts with duplicated code. |
| **Production quality** | Atomic writes (temp + rename); validates `upload_id` before building a path; never lets an `LLMError` escape as a 500; clear error messages; uses the injected clock; no global mutable state; timeouts on every call. | Writes files in place, uses `time.sleep`, bare `except:`, a single model failure turns the whole request into a 500, upload id used directly in a path. |
| **Testing** | Tests written alongside the code: table-driven validation tests, an API round-trip test, fault-injection tests for fenced/malformed/wrong-label/non-retryable cases, and a backoff test asserting `clock.sleeps`. | One happy-path test written at the end, or only manual curl checks; no test drives the mock into a failure mode. |
| **End-to-end ownership** | Runs the server and curls it with the sample file at least once; reads the sample data before coding and points out the broken rows; finishes with a quick summary of what is done, what isn't, and what they would do next. | Stops at "the function returns the right thing" without wiring the endpoint; never looks at `data/`; leaves TODOs unexplained. |
| **Communication** | Narrates trade-offs ("I'll read the whole file now; for 100x I'd stream"), asks one or two sharp clarifying questions (e.g. "do duplicates of invalid rows count?") and confirms the answer is in the spec. | Silent for long stretches, or asks questions the spec answers explicitly; can't explain why a retry is or isn't safe. |

## Hidden-test mapping

| Test file | Covers |
|---|---|
| `test_part1.py` | counts, row/field errors, stripping, quoted newlines, BOM, header-only, 400/415/422/404, rule order, duplicate-of-valid, JSONL (`change`) |
| `test_part2.py` | labels, order, persistence + GET, fence/case normalization, each fault type once, 3-attempt cap, bad confidence, non-retryable, `timeout=10`, `<item>` tags |
| `test_part3.py` | backoff ranges and jitter, Retry-After, no final sleep, concurrency used and bounded (incl. 1), idempotent re-run |

Use hidden-test results as evidence for **Correct execution** only; the other
categories come from watching the candidate work.
