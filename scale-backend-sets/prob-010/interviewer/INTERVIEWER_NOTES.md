# prob-010 — Document Triage with Confidence Routing (interviewer notes)

**Mimics:** the reported real round (upload a file → JSON → LLM classification →
persist), in its "clone a starter repo and extend it" form: ingestion and
classification already exist and work; the candidate adds human-in-the-loop
routing by model confidence, a review queue, and an audit trail, then hardens
them against concurrent reviewers, re-runs and inconsistent model answers.
**Difficulty:** medium · **Mode:** FastAPI + SQLite · **Starter:** existing repo (~350 lines, 9 passing tests) · **Planted bugs:** none

## Setup

```bash
python tools/export_candidate.py prob-010 ~/interview --part1-only   # give the candidate prob-010/
# afterwards, from scale-backend-sets/:
SOLUTION_DIR=~/interview/prob-010 python -m pytest prob-010/interviewer/hidden_tests -q
SOLUTION_DIR=... python -m pytest prob-010/interviewer/hidden_tests/test_part2.py -m "not change"   # reason rule not delivered
```

The hidden tests build the app with
`create_app(storage_dir=tmp, llm=..., clock=FakeClock(start=1_700_000_000), auto_accept_threshold=..., consistency_samples=...)`
and use only the HTTP API, so the candidate may restructure `app/` freely. They
use their own documents and a copy of the keyword map with each test document's
confidence pinned by a `Ref D-00n` marker in its text, so the outcome does not
depend on how the candidate words the prompt, only on the document text being
inside `<item>` tags (the starter's prompt already does this). If the candidate
renamed `create_app` or changed its parameters, fix the import in a scratch copy
rather than failing them outright.

The repo has no module-level `app`; it runs with `uvicorn --factory app.main:create_app`
(the README says so). The schema uses `CREATE TABLE IF NOT EXISTS`, so after
adding columns a stale `./storage/intake.db` keeps the old table; tests use
`tmp_path` and are unaffected. Point this out only if they get stuck on it.

## What the candidate should take from reading the code first (minutes 0–5)

A strong candidate reads `main.py`, `db.py`, `classifier.py` (and skims
`ingest.py`) before typing and can say:

* `DocumentStore` owns all SQL and all timestamps; every public method is **one
  `BEGIN IMMEDIATE` transaction**. So new logic belongs in the store as one method
  per operation (check the status *and* change it in the same transaction), not
  in route handlers chaining `get_…` and `save_…` calls. This is the whole of
  Part 3's concurrency story, and it is visible on line 1 of `connect()`.
* `classify_batch` calls the model **outside** any transaction (good: never hold
  the SQLite write lock across a network call) and then calls `save_classification`,
  which **overwrites unconditionally**. That is the hook for routing in Part 1 and
  the re-run hazard in Part 3.
* The classify route re-classifies **every** document on every call ("again, if
  it was classified before"). Fine today; destructive once humans review.
* `Classification.error` is set exactly when the classification failed, and then
  `label`/`confidence` are `None`: routing needs that branch.
* `doc_id` is `UNIQUE` across all batches, so `GET /documents/{doc_id}` is
  well-defined; upload order is the `seq` column (under `FakeClock` every
  `created_at` is equal).
* `create_app` already accepts `auto_accept_threshold` and `consistency_samples`;
  nothing reads them yet.

## Timeline

### 60-minute mode

| min | what happens |
|---|---|
| 0–5 | Hand over `PART1.md`. Candidate reads `app/`, runs the 9 existing tests, maybe curls `data/documents.jsonl`. |
| 5–22 | Status columns, routing rule, `GET /documents/{id}`, review queue order, review endpoint with 422/404/409, tests. Reveal `PART2.md` once a low-confidence document can be reviewed in a test. |
| 22–32 | Part 2: audit table, events at upload / classify / review in the same transaction, `GET /documents/{id}/audit`. |
| ~32 | **Drop the mid-part change** (below), once a review appends a `reviewed` event. |
| 32–42 | Reason rule, `GET /audit` filters, restart test. Reveal `PART3.md`. |
| 42–55 | Part 3: version + compare-and-set review, a threaded test, re-run skips non-`ingested`, two-sample consistency. |
| 55–60 | Follow-up discussion (pick 1–2 of the questions below). |

If the candidate is behind at minute 25, reveal Part 2 anyway and let the queue
ordering edge cases go. If they are behind at minute 45, skip the
self-consistency code and ask them to explain where their review is racy instead.

### 30-minute mode (Part 1 plus the start of Part 2)

| min | what happens |
|---|---|
| 0–4 | Hand over `PART1.md`; insist on reading the code first. |
| 4–20 | Routing, `GET /documents/{id}`, review endpoint with 409/422, queue. Ordering ties are optional. |
| 20–22 | Reveal `PART2.md`. |
| 22–28 | Audit table and the `ingested` / `classified` / routing events, ideally one test reading `/documents/{id}/audit`. |
| 28–30 | One follow-up question (#1 below). |

Score Part 3 categories as "not observed"; run `test_part1.py` and `test_part2.py -m "not change"`.

## Mid-part requirement change (Part 2, ~minute 32)

Say, verbatim:

> "Compliance came back with one more rule before this ships: when a reviewer
> overrides the model, we need to know why. If the document has a model label
> and the reviewer's `label` is different, the review request must include a
> `reason`: a string that is not empty after trimming whitespace. If it is
> missing, `null` or blank, reply 422 and change nothing. When the reviewer
> agrees with the model, or the classification failed so there is no model
> label, `reason` is optional. Store the trimmed reason in the `reviewed`
> event's details as `reason`, or `null` if none was given. This check comes
> after the 404 and 409 checks."

What it tests: whether the review logic is one place (a store method) that can
take one more precondition cleanly, whether they keep "a rejected request
appends nothing" true, and whether they notice the rule needs the stored model
label (not something the client sends).
Hidden tests: every `test_part2.py` test marked `change`
(`test_override_*`, `test_agreeing_needs_no_reason`, `test_no_model_label_needs_no_reason`,
`test_reason_rule_comes_after_status_check`). The non-change tests always send a
`reason` when they override, so they pass with or without the rule.

## Planted bugs

None. The starter code is correct; the challenge is reading it and extending it
in the right layer.

## Hint ladder

Give the lowest hint that unblocks; note each hint in the rubric.

**Part 1**
1. "Where does a classification get written today, and what would you have to change for it to also decide the status?" (`save_classification`; route in the same UPDATE)
2. "Write the rule as a pure function of the `Classification` and the threshold. What are the three outcomes?" (auto / low_confidence / classification_failed; `>=` at the boundary)
3. "The queue is 'oldest first'. Under `FakeClock`, what makes two documents differ if their timestamps are equal?" (a `routed_at` column, ties by `seq`)

**Part 2**
1. "If the process dies between updating the document and writing the event, what does compliance see?" (same transaction; the store's `connect()` already gives you one)
2. "How will `seq` keep increasing after a restart?" (`INTEGER PRIMARY KEY AUTOINCREMENT`; for a JSONL file, read the last line at startup)
3. "Write the filter query once: a list of `(clause, value)` pairs where only non-null ones are used, values as parameters."

**Part 3**
1. "Two reviewers click 'submit' at the same moment. Walk me through what each request reads and writes." (both see `needs_review`, both update)
2. "Can the status check and the update be one statement, or one transaction?" (`UPDATE … WHERE doc_id = ? AND status = 'needs_review' AND version = ?` + `rowcount`, or check inside the store's `BEGIN IMMEDIATE`)
3. "On a re-run, which documents should the model ever see again?" (only `ingested`; and re-check that under the write lock when recording, because two runs can overlap)

## Common pitfalls (what the hidden tests catch)

* `confidence > threshold` instead of `>=` (the 0.80 document in the tests is the boundary).
* A failed classification (`label: None`) crashes routing or is auto-accepted at threshold 0.
* Queue ordered by `created_at` or `doc_id` instead of time-entered-queue then upload order.
* Review validates the label case-insensitively or accepts `"Contract"`; blank reviewer accepted; reviewer not stripped.
* 409 vs 422 confusion: reviewing an `auto_accepted` document returns 422 or 200.
* Route handler does `get_document` → check → `save_…` across separate store calls: works in
  single-threaded tests, fails the 8-thread test (two 200s, two `reviewed` events).
* Audit events written after the commit of the status change, or from the route handler in a
  second transaction; or the `classified` event appended only on success.
* Events appended for rejected (4xx) requests, e.g. "review_attempted".
* `seq` from an in-memory counter (restarts at 1) or `len(file)`; `ts` from `time.time()`.
* `since` compared as a string; unknown `action` silently returns `[]` instead of 422.
* Part 3: re-run still re-classifies `needs_review` documents whose classification failed (the
  spec says leave them for a human); counting skipped documents in `classified`.
* Part 3: concurrent classify runs record a document twice because the "is it still ingested?"
  check happened before the model call, not at write time.
* Self-consistency: averaging confidences instead of taking the minimum; running the second
  sample after the first failed; `attempts` counting only one sample.

## Follow-up questions

**1. "The review queue is 100x bigger: 50,000 documents waiting, 30 reviewers. What changes?"**
A strong answer covers: prioritisation instead of FIFO (SLA deadline per customer tier
or document type, age, business value; ID documents blocking onboarding first);
claiming work with a **lease** (`claimed_by`, `claim_expires_at`) so two reviewers never
open the same document, with `SELECT … FOR UPDATE SKIP LOCKED` (or a conditional
`UPDATE … RETURNING`) on Postgres; pagination of the queue and an index on
`(status, priority, routed_at)`; per-reviewer skill routing (IDs only to trained staff);
metrics: queue depth, age of oldest item, time-to-review p95, SLA breaches, alerting;
back-pressure when the queue grows faster than it drains (temporarily lower the bar,
add reviewers, or pause intake for that customer); sampling a small fraction of
auto-accepted documents into the queue as a quality check.

**2. "How would you choose `auto_accept_threshold`? Is 0.8 right?"**
Strong: use the reviewed documents as labelled data (reviewer label vs model label
and confidence) to measure precision at each threshold, and pick the lowest threshold
that keeps auto-accepted precision above a target (say 99%) while watching review
volume; calibration curves (is "0.9" right 90% of the time?) and recalibration (isotonic /
Platt) if not; **per-label** thresholds (an ID document mistake costs more than a
newsletter); beware selection bias (you only get human labels for low-confidence
items, so sample some high-confidence ones for review too); re-evaluate on every
prompt or model change; confidence self-reported by an LLM is often poorly calibrated,
so agreement across samples or a separate verifier can be a better signal; the two-sample
disagreement rule from Part 3 is one such signal.

**3. "An auditor asks how they can trust that nobody edited the audit log. And how long do we keep it?"**
Strong: today's guarantees are only "the app never updates or deletes" (plus triggers
in the reference); a DB admin can still rewrite rows. Make it tamper-*evident*: a hash
chain (each event stores `hash(prev_hash + canonical event JSON)`), periodically anchor
the head hash somewhere the DB admin can't write (WORM/object-lock storage, a separate
account, a signed daily digest); verify the chain in a job and alert on breaks.
Separate the audit store's write path and credentials from the app DB; ship events
to an append-only external log (S3 object lock, a SIEM). Retention: driven by contract
and regulation (often years for financial or identity records), with legal holds;
the documents' text may contain PII, so keep PII out of event details (reference ids,
not content), so the trail can outlive document deletion under GDPR erasure requests;
partition by month for cheap archival; clock and ordering: `seq` from one writer, `ts`
from a synced clock.

## Reference solution

`reference/app/`:
* `routing.py`: `route(classification, threshold) -> Route(status, final_label, review_reason)`, a
  pure function (`classification_failed` → `disagreement` → threshold).
* `db.py`: new document columns (`status`, `final_label`, `review_reason`, `reviewed_by`,
  `routed_at`, `version`); an `audit_events` table with `AUTOINCREMENT` `seq` and triggers that
  reject `UPDATE`/`DELETE`. `record_classification` re-checks `status = 'ingested'` inside the
  store's `BEGIN IMMEDIATE` transaction, writes the classification and route, and appends
  `classified` + the routing event, or does nothing if another run got there first. `review`
  checks 404 → 409 (status, then `expected_version`) → 422 (reason rule), updates, and appends
  `reviewed`, all in one transaction. `audit_events` builds the filter from constant clauses
  with bound values.
* `classifier.py`: `classify(doc, samples=1|2)`; the existing retry loop became `_sample`.
* `main.py`: `ReviewRequest` (strip + non-blank reviewer, exact label, blank reason → `None`),
  domain exceptions → 404/409/422, the re-run filter, `Literal` action filter (422), settings validation.

Lines a candidate must add (reference minus starter, from `tools/verify_problem.py`): **214** in total.
Approximate split: Part 1 ≈ 95 (columns, routing, document/queue/review endpoints, error mapping),
Part 2 ≈ 70 (audit table, three append sites, two endpoints with filters, reason rule ≈ 8),
Part 3 ≈ 50 (version + compare-and-set, re-run filter and write-time re-check, two-sample
classification, settings validation) plus discussion.
