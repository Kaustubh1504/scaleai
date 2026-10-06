# prob-004 — Annotation Task Leasing Service (interviewer notes)

**Mimics:** the "clone a starter repo and extend it" variant of the round, on
Scale's own domain: annotators claim tasks under a lease, several annotators
label each task, and the service computes consensus.
**Difficulty:** medium · **Mode:** FastAPI + SQLite · **Starter:** existing repo (~270 lines, 6 passing tests) · **Planted bugs:** 2

## Setup

```bash
python tools/export_candidate.py prob-004 ~/interview --part1-only   # give the candidate prob-004/
# afterwards, from scale-backend-sets/:
SOLUTION_DIR=~/interview/prob-004 python -m pytest prob-004/interviewer/hidden_tests -q
SOLUTION_DIR=... python -m pytest prob-004/interviewer/hidden_tests/test_part2.py -m "not change"   # gold tasks not delivered
```

The hidden tests build the app with `create_app(storage_dir=tmp, clock=FakeClock(start=1_700_000_000), lease_seconds=..., redundancy=...)`
and use only the HTTP API, so the candidate may restructure `app/` freely. If they
renamed `create_app` or changed its parameters, fix the import in a scratch copy
rather than failing them outright.

The repo has no module-level `app`; it runs with `uvicorn --factory app.main:create_app`
(the README says so). Point this out only if they get stuck on it.

## What the candidate should take from reading the code first (minutes 0–5)

A strong candidate reads `main.py`, `db.py` and `models.py` before typing and can say:

* `TaskStore` owns all SQL and all timestamps (`self.clock.time()`), and opens a
  short-lived connection per method, so it is already thread-safe. New logic
  belongs in `TaskStore`, as transactions, not in route handlers doing several store calls.
* `create_app` accepts a `clock` and `TaskStore` accepts a `clock`, but **main.py
  never passes it on** (planted bug 1). Spotting this while reading is a strong signal.
* Creation order is the `seq` column, not `created_at` (all tasks in a batch share a
  timestamp, and under `FakeClock` every task does).
* `submissions` has `task_id` as its primary key and is written with
  `INSERT OR REPLACE`: one submission per task is baked into the schema (planted bug 2;
  harmless with redundancy 1, which is why it shipped).
* `x_annotator_id: str = Header(...)` makes FastAPI answer **422**, not the 400 the spec wants.
* `with conn:` in Python's `sqlite3` commits/rolls back, but it does **not** start a
  transaction until the first `INSERT/UPDATE/DELETE`; a `SELECT` followed by an
  `UPDATE` in the same block is not atomic against other connections (this is Part 3).

## Timeline

### 60-minute mode

| min | what happens |
|---|---|
| 0–5 | Hand over `PART1.md`. Candidate reads `app/`, runs the existing tests, maybe curls the server. |
| 5–22 | Leases table or columns, claim / extend / submit, header check, state derivation. **Planted bug 1** surfaces as soon as they write a `FakeClock` test for expiry. Reveal `PART2.md` once a lease expires correctly in a test. |
| 22–32 | Part 2: slot counting in the claim query, "never again" rule, consensus on the last submission. **Planted bug 2** surfaces on the first 3-annotator test. |
| ~32 | **Drop the mid-part change** (below), once a 3-vote task reaches `completed` or `disputed`. |
| 32–42 | Gold tasks + stats endpoint, tests. Reveal `PART3.md`. |
| 42–55 | Part 3: make claim/submit atomic (`BEGIN IMMEDIATE`), a threaded test, restart test. |
| 55–60 | Follow-up discussion (pick 1–2 of the questions below). |

If the candidate is behind at minute 25, reveal Part 2 anyway and let `extend` go.
If they are behind at minute 45, skip Part 3 code and go to the discussion; ask them
to explain where their claim is racy instead.

### 30-minute mode (Part 1 plus the start of Part 2)

| min | what happens |
|---|---|
| 0–4 | Hand over `PART1.md`; insist on reading the code first. |
| 4–18 | Claim with a lease, expiry, submit by holder only. Planted bug 1 is in scope; give hint 2 by minute 14 if they are stuck on it. `extend` is optional. |
| 18–20 | Reveal `PART2.md`. |
| 20–27 | Redundancy in the claim query, ideally one 3-annotator test (which exposes planted bug 2). |
| 27–30 | One follow-up question (#1 below). |

Score Part 3 categories as "not observed"; run `test_part1.py` and `test_part2.py -m "not change"`.

## Mid-part requirement change (Part 2, ~minute 32)

Say, verbatim:

> "Quality team request: some tasks are gold tasks, known-answer checks we mix
> into the queue. A task created with a `gold_label` field is a gold task; the
> gold label must be one of the task's labels, otherwise that batch entry is
> rejected like any other invalid entry. Gold tasks are leased, labelled and
> resolved exactly like normal tasks, but annotators must never see the answer,
> so `gold_label` must not appear in the claim response. Add
> `GET /annotators/{annotator_id}/stats` returning `{"gold_seen", "gold_correct",
> "accuracy"}`: how many gold tasks this annotator submitted, how many of those
> matched the gold label, and `gold_correct / gold_seen` rounded to 2 decimals,
> or `null` if `gold_seen` is 0. Unknown annotators get zeros, not a 404."

What it tests: whether they extend the existing validation model (`NewTask`) and
schema cleanly, compute stats from stored submissions (one `JOIN`) instead of
keeping counters in memory, and think about leaking the answer.
Hidden tests: every `test_part2.py` test marked `change` (`test_gold_*`, `test_claim_does_not_reveal_gold_label`).

## Planted bugs

Both are deterministic and invisible to the existing tests (they never check a
timestamp and never submit twice to one task). Neither shows up when curling a
real server with `RealClock`, which is why they shipped. Line numbers are in
`candidate/`.

### Bug 1: the injected clock never reaches the store (`app/main.py:34`)

```python
store = TaskStore(storage_dir / "tasks.db")          # clock not passed: TaskStore uses RealClock
```

* **Symptom:** in a `FakeClock` test, `lease_expires_at` is real wall-clock time + 60
  (e.g. `1791234567.8`, not `1700000060.0`), and `clock.advance(61)` does not expire the
  lease: the second annotator still gets 204. `created_at` is also wall-clock time. If the
  candidate computes the expiry from `clock` in `main.py` but compares it with the store's
  time (or vice versa), leases look expired immediately (fake 2023 < real now) and everyone
  gets the same task again, which looks like the original bug.
* **Root cause:** `create_app` resolves `clock` and uses it for `/health`, but builds the
  store without it; `TaskStore.__init__` silently falls back to `RealClock()`.
* **Fix:** `TaskStore(storage_dir / "tasks.db", clock=clock)`. Better: make `clock` a
  required argument of `TaskStore` so this cannot recur; mention that the silent default is the real defect.
* **Hint ladder:**
  1. "Print `lease_expires_at` in your test next to `clock.time()`. Are they on the same clock?"
  2. "Where does the store get its time from, and who constructs the store?"
  3. Point at `main.py:34`.

### Bug 2: one submission per task is baked into the schema (`app/db.py:32` and `app/db.py:107-112`)

```sql
task_id TEXT PRIMARY KEY REFERENCES tasks (id),   -- submissions table
```
```python
# Upsert: a client retrying the same request must not create a duplicate row.
conn.execute("INSERT OR REPLACE INTO submissions ...")
```

* **Symptom:** with `redundancy=3`, three annotators submit but `GET /tasks/{id}` shows
  only the **last** submission; the task stays `pending` forever, and annotators whose
  submission was replaced can claim it again. If the candidate replaces `INSERT OR REPLACE`
  with `INSERT` but keeps the key, the second submission is a 500:
  `sqlite3.IntegrityError: UNIQUE constraint failed: submissions.task_id`.
* **Root cause:** the primary key makes a second row for the same task a conflict, and
  `OR REPLACE` resolves it by deleting the earlier row. The comment gives a plausible but
  wrong reason (idempotency belongs to the lease check, not a silent overwrite).
* **Fix:** `PRIMARY KEY (task_id, annotator_id)` and a plain `INSERT`. Because the schema
  uses `CREATE TABLE IF NOT EXISTS`, an existing `storage/tasks.db` keeps the old table:
  delete it locally. A strong candidate says that production needs a migration (new table,
  copy rows, swap) and a schema version.
* **Hint ladder:**
  1. "After three submissions, what does `GET /tasks/{id}` show? How many rows are in `submissions`?"
  2. "Look at the `submissions` table definition. What is unique there?"
  3. "What does `INSERT OR REPLACE` do when the key already exists?"

## Hint ladder

Give the lowest hint that unblocks; note each hint in the rubric.

**Part 1**
1. "Where would you store the lease so that it survives a restart and so that expiry needs no background job?" (an `expires_at` column or a `leases` table; compare with `now` on every read)
2. "How does `GET /tasks/{id}` know a lease expired if nobody has called claim since?" (derive `leased` from `expires_at > now`, or reap expired leases before every read)
3. "Write the claim as: return my live lease if I have one; else find the oldest claimable task; insert a lease." Then point at planted bug 1 if a FakeClock test is failing.

**Part 2**
1. "Write the claimability rule from PART2.md as a single SQL `WHERE` clause." (`NOT EXISTS my submission AND submissions + live leases < redundancy`)
2. "When exactly do you compute consensus, and in which transaction?" (in `submit`, when the count reaches `redundancy`, same transaction as the insert)
3. Planted bug 2 ladder above.

**Part 3**
1. "Two requests run your claim at the same time. Walk me through the interleaving." (both SELECT the same row, both INSERT a lease)
2. "What does Python's `sqlite3` do when you run a `SELECT` inside `with conn:`? When does the transaction start?" (only at the first write; use `isolation_level=None` + `BEGIN IMMEDIATE`, or a single conditional `UPDATE ... WHERE ...` checked with `rowcount`)
3. "Write the test first: a `threading.Barrier(20)`, 20 threads calling claim, assert no task is granted twice."

## Common pitfalls (what the hidden tests catch)

* Using `time.time()` (or the store's unfixed clock) anywhere: leases never expire under `FakeClock`.
* Treating `expires_at == now` as live (the spec says live while `now < expires_at`).
* Updating a `state` column on claim but never resetting it on expiry, so `GET` and `?state=` keep saying `leased`.
* Re-claim by the lease holder extends the lease, or hands them a second task.
* `Header(...)` left in place: missing header is 422, not 400; blank header accepted.
* Submit checks the label before the lease (422 instead of 409 for a non-holder), or a 422 drops the lease.
* Ordering by `created_at` (ties within a batch) or by `id` text (`t10` < `t2`) instead of creation order.
* Part 2: counting only leases or only submissions toward the slot limit; letting an annotator whose lease expired after submitting claim again; `agreement` not rounded; `consensus_label` set on a disputed task.
* Part 2 change: `gold_label` leaked in the claim response; accuracy counters kept in memory (lost on restart) instead of computed from submissions.
* Part 3: check-then-act across separate connections or separate store calls. (Measured: the reference
  with `BEGIN IMMEDIATE` replaced by Python's default implicit transactions passes Parts 1–2 and fails
  3–4 Part 3 tests on every run, because the `SELECT` is outside the write lock.)
  Also: a module-level `threading.Lock` (works in-process, breaks with 2 uvicorn workers; acceptable if they say so); one shared `sqlite3` connection with `check_same_thread=False` and no lock, which can fail intermittently under load (cursor misuse, interleaved transactions).
* Any in-memory state (lease dicts, counters): the restart tests fail.

## Follow-up questions

**1. "Some tasks take 20 seconds, some take 20 minutes. How long should a lease be?"**
A strong answer covers: short leases plus heartbeats (`extend` every lease/3 from the UI)
rather than one long lease, so abandoned work is recycled in minutes; per-task-type or
per-project lease lengths from observed p95 durations; a cap on total extensions so a
stuck tab can't hold a task forever; what the annotator sees when their lease expired
mid-task (409 on submit; the UI should warn before expiry, and the work could be accepted
if nobody else has claimed it yet, as a product decision); metrics on expiry rate and on
work lost to expiry; fencing tokens (a lease id or version returned by claim and required
on submit) so a stale holder can never submit over a newer lease.

**2. "The annotator UI and this service run on machines whose clocks disagree by a few seconds. What breaks?"**
Strong: only the server's clock may decide liveness; the client should get a relative
`expires_in` (or compute from server time in the response), never compare its own clock
with `expires_at`; with several service instances, use the database's clock (`now()` in
Postgres) or a single time source rather than each host's clock; keep a safety margin
(the client stops working a few seconds before expiry); NTP drift and leap smearing;
monotonic clocks for durations inside one process, wall clock only for persisted
deadlines; the fencing-token idea makes skew safe because ownership is checked by
identity, not by time alone.

**3. "`POST /tasks/claim` must handle 1,000 requests per second. What breaks first and what do you change?"**
Strong: SQLite's single writer lock serializes every claim; move to Postgres and claim
with `SELECT ... FOR UPDATE SKIP LOCKED LIMIT 1` (or a single `UPDATE ... WHERE id = (SELECT ...)
RETURNING`) so concurrent claimers skip each other's rows instead of all contending for the
"oldest" one; indexes that make the claimable query an index range scan (state, seq) and
counters (`submission_count`, `lease_count`) on the task row instead of `COUNT(*)` subqueries;
shard the queue (by project, or N partitions with annotators hashed to a starting
partition) to spread contention; pre-assign batches of tasks to annotators (prefetch 5)
to cut request rate; fairness: strict FIFO is a hotspot, approximate order is usually
fine; starvation of old tasks whose annotators keep getting excluded (the "never again"
rule) needs monitoring; a periodic reaper instead of lazy expiry once the leases table is big.

## Reference solution

`reference/app/`:
* `db.py`: `TaskStore` with `connect(write=True)` = `isolation_level=None` +
  `BEGIN IMMEDIATE` (WAL for readers); a `leases` table keyed `(task_id, annotator_id)`;
  submissions keyed `(task_id, annotator_id)`; `claim` deletes expired leases, returns the
  caller's live lease if any, else runs one claimable query (`state = 'pending' AND NOT EXISTS
  my submission AND submissions + leases < redundancy ORDER BY seq`) and inserts the lease, all
  in one transaction. `leased` is derived in `_view` from live leases, so expiry needs no
  writes. `submit` checks 404 → 409 → 422, swaps the lease for a submission and finalises in
  the same transaction. Domain exceptions map to HTTP codes in `main.py`.
* `consensus.py`: `decide(labels, redundancy) -> Outcome(state, consensus_label, agreement)`.
* `models.py`: `gold_label` with a "must be one of labels" validator.
* `main.py`: clock passed to the store (bug 1), `X-Annotator-Id` dependency (400), exception handlers.

Lines a candidate must add (reference minus starter, from `tools/verify_problem.py`): **213** in total.
Approximate split: Part 1 ≈ 115 (leases, claim/extend/submit, derived state, header, error
mapping, bug 1), Part 2 ≈ 70 (slot rule, consensus, bug 2, gold ≈ 25), Part 3 ≈ 30
(`BEGIN IMMEDIATE` transactions, WAL, busy timeout) plus discussion.
