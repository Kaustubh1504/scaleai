# prob-001 — Support Ticket Ingestion & LLM Triage (interviewer notes)

**Mimics:** the reported real round. Part 1 is a POST endpoint that converts an
uploaded file to JSON and saves it locally; Part 2 sends the data to an LLM for
classification and persists the results.
**Difficulty:** medium · **Mode:** FastAPI · **Starter:** minimal skeleton · **Planted bugs:** none

## Setup

```bash
python tools/export_candidate.py prob-001 ~/interview --part1-only   # give the candidate prob-001/
# afterwards, from scale-backend-sets/:
SOLUTION_DIR=~/interview/prob-001 python -m pytest prob-001/interviewer/hidden_tests -q
SOLUTION_DIR=... python -m pytest prob-001/interviewer/hidden_tests/test_part1.py -m "not change"   # JSONL not delivered
```

The hidden tests build the app with `create_app(storage_dir=tmp, llm=..., clock=FakeClock())`
and use their own fixture copies, so candidate edits to `data/` or
`mock_services/` cannot change the outcome. If the candidate renamed
`create_app` or moved it, fix the import in a scratch copy rather than failing them outright.

## Timeline

### 60-minute mode

| min | what happens |
|---|---|
| 0–3 | Hand over `PART1.md`. Candidate reads `app/main.py`, `data/tickets.csv`, `mock_services/llm.py`. |
| 3–12 | CSV parsing + validation. Expect them to open `tickets.csv` and notice the broken rows. |
| ~12 | **Drop the mid-part change** (below), once the happy path for CSV works. |
| 12–22 | JSONL support, storage, GET endpoint, tests. Reveal `PART2.md` once uploads round-trip. |
| 22–42 | Part 2: prompt, parsing, validation, retry cap, persistence, tests with injected faults. |
| 42–55 | Part 3: backoff + Retry-After, bounded concurrency, idempotent re-run. |
| 55–60 | Follow-up discussion (pick 1–2 of the questions below). |

If the candidate is behind at minute 25, reveal Part 2 anyway and let Part 1 edge cases go.
If they are behind at minute 45, skip Part 3 code and go to the discussion.

### 30-minute mode (Part 1 plus the start of Part 2)

| min | what happens |
|---|---|
| 0–2 | Hand over `PART1.md`. |
| 2–15 | CSV upload, validation, storage. Skip the mid-part change unless they finish by minute 12. |
| 15–17 | Reveal `PART2.md`. |
| 17–27 | Prompt + parse + validate + retry cap for one ticket, ideally with one fault-injection test. |
| 27–30 | One follow-up question (#1 below). |

Score Part 3 categories as "not observed"; run `test_part1.py -m "not change"` and `test_part2.py`.

## Mid-part requirement change (Part 1, ~minute 12)

Say, verbatim:

> "Product just told us that some customers export JSONL, not CSV. Please also
> accept `.jsonl` files: one JSON object per line with the same five keys. Skip
> blank lines. A line that isn't valid JSON, or isn't a JSON object, is an
> invalid row with `field: null`. A value that isn't a string counts as missing
> for that field. Extra keys are ignored. Everything else (rules, response,
> storage) is the same."

What it tests: whether validation was written against a parsed record
(easy to extend) or tangled with `csv` (painful). Strong candidates refactor to
"parser yields records → shared validator" in a few minutes.
Hidden tests: `test_part1.py::test_jsonl_upload` (marker `change`).

## Planted bugs

None. This is a skeleton problem.

## Hint ladder

Give the lowest hint that unblocks; note each hint in the rubric.

**Part 1**
1. "What does `csv.DictReader` do with a row that has too few or too many values?" (restval `None`, extras under key `None`)
2. "Multi-line quoted fields: how are you feeding the text to the csv module?" (`io.StringIO(text, newline="")`; don't `splitlines()` a CSV)
3. "Consider splitting this into: decode → iterate records → validate each record → build the response."

**Part 2**
1. "Print `resp.text` for a few calls with `fenced_rate=1.0` or `malformed_rate=1.0`. What do you see?"
2. "Which exceptions are worth retrying? Look at `LLMError.retryable`."
3. "Write the per-ticket function first: `classify(ticket) -> result dict`, and loop over it."

**Part 3**
1. "Where does the waiting happen in your retry loop, and which clock is it using?" (must be `clock.sleep`)
2. "How would you run several tickets at once and still keep result order?" (`ThreadPoolExecutor.map`, or `asyncio.gather` + `Semaphore`)
3. "On a re-run, what does the persisted file already tell you?"

## Common pitfalls (what the hidden tests catch)

* Row numbering off by one (header counted, or blank lines counted).
* Duplicate check against *all* earlier ids, not just valid ones.
* `csv.reader` over `text.splitlines()` breaks quoted newlines.
* `time.sleep` instead of `clock.sleep` (tests see no sleeps, or tests become slow).
* Not passing `timeout=10`, so a slow model "succeeds" after 15 s.
* Retrying `ContextLengthExceededError` (non-retryable) three times.
* Treating `confidence: true` as valid (`bool` is an `int` subclass).
* Sleeping after the final attempt.
* Re-run re-classifies everything, or loses the earlier results.
* Upload id used in a file path without validation (path traversal). Not a hidden test, but worth raising.

## Follow-up questions

**1. "The same ticket gets `billing` on Monday and `bug` on Tuesday. What do you do?"**
A strong answer covers: temperature 0 / fixed seed where the provider allows;
caching by content hash (same input → same stored answer, and cheaper);
self-consistency (n samples, majority vote, escalate when they disagree);
logging prompt version + model version with each result so drift is attributable;
an eval set of labelled tickets run on every prompt/model change; routing
low-confidence or disagreeing cases to a human queue.

**2. "We run 20 instances of this service and the provider allows 600 requests/minute in total. How do you stay under it?"**
Strong: a shared limiter (Redis token bucket or a central dispatcher) rather than 20 local
limiters at 30/min, which waste capacity when load is uneven; still honour
`Retry-After` as the source of truth; client-side concurrency caps; jittered backoff to
avoid synchronized retry storms; per-tenant fairness so one big upload can't starve
others; alerting on the 429 rate. Bonus: batching several tickets per call (`<items>`) cuts request count.

**3. "Uploads become 100x larger (200k tickets) and classification takes 20 minutes. What changes?"**
Strong: make classify asynchronous: `POST` returns `202` + job id, workers pull
from a durable queue, `GET /jobs/{id}` shows progress; stream the upload to disk and parse
incrementally instead of `await file.read()`; store per-ticket results in SQLite/DB
rows instead of rewriting one big JSON file; checkpointing so a crashed worker resumes
(the idempotent re-run from Part 3 is the seed of this); a dead-letter list for tickets that
keep failing; cost estimation and budget limits before starting; batching.

## Reference solution

`reference/app/`: `ingest.py` (decode → parser generator → shared validator),
`classifier.py` (prompt, fence-tolerant parser, `RetryPolicy` with equal jitter),
`storage.py` (atomic temp-file + `os.replace` writes, id validation), and `main.py` (routes,
per-upload lock, `ThreadPoolExecutor.map` for bounded, ordered concurrency).

Approximate lines a candidate must write: Part 1 ≈ 115 (including JSONL ≈ 15),
Part 2 ≈ 85, Part 3 ≈ 30 plus discussion.
