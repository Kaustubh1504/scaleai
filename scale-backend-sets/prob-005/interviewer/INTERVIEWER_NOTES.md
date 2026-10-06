# prob-005 — Webhook Delivery Dispatcher (interviewer notes)

**Mimics:** the "clone a starter repo and extend it" variant of the round, applied to a
plain-Python background process: correct webhook delivery with an audit trail (Part 1),
scheduled retries and dead-lettering (Part 2), durable state that survives restarts and
crashes (Part 3).
**Difficulty:** medium · **Mode:** plain Python (library + CLI, no web framework) ·
**Starter:** existing repo (~330 lines) · **Planted bugs:** none

## Setup

```bash
python tools/export_candidate.py prob-005 ~/interview --part1-only   # give the candidate prob-005/
# afterwards, from scale-backend-sets/:
SOLUTION_DIR=~/interview/prob-005 python -m pytest prob-005/interviewer/hidden_tests -q
SOLUTION_DIR=... python -m pytest prob-005/interviewer/hidden_tests/test_part2.py -m "not change"   # change not delivered
```

The hidden tests build the dispatcher as
`Dispatcher(state_dir, EventStore(path), load_subscriptions(path), http, FakeClock(), **kw)`,
importing from `dispatcher.dispatcher`, `dispatcher.events` and `dispatcher.subscriptions`.
They write their own events and subscriptions files and route each subscription to its own
`WebhookReceiver` (which verifies signatures on the same FakeClock), so candidate edits to
`data/` or `mock_services/` cannot change the outcome. One Part 3 test runs the candidate's
code in a subprocess and kills it with `os._exit` mid-run. If the candidate renamed a module,
fix the import in a scratch copy rather than failing them outright.

## What the candidate should learn from reading the code first (minutes 0–5)

A strong candidate reads all five files before typing and notices:

* `Subscription.wants()` already handles `"*"`, and the dispatcher already uses it. Routing is done.
* `signing.py` already implements the receiver's scheme. Nothing to reinvent. Its docstring
  says to sign **the bytes you send**, and the starter posts with `json=`, which re-serializes.
  The fix is `content=body` with the same `body` that was signed.
* `EventStore.read()` already validates lines with `Event.from_dict`, but **swallows** bad
  lines with a log warning. Part 1 needs the line numbers, plus duplicate-id detection.
* `DispatchReport` already has the fields the spec names. `delivery()` is a stub.
* `max_attempts` and `timeout_s` are accepted but unused ("not used yet").
* The CLI wires `RealClock` and a real `httpx.Client`, and `main()` accepts `http=`/`clock=`
  overrides, so the CLI is testable without a server.
* The starter catches `httpx.HTTPError` around the POST. That is the right boundary, and Part 3
  relies on non-httpx exceptions propagating.

Ask "what did you notice?" at minute 5 if they haven't said. It is evidence for
*systematic thinking* and *end-to-end ownership*.

## Timeline

### 60-minute mode

| min | what happens |
|---|---|
| 0–5 | Hand over `PART1.md`. Candidate reads the repo and `data/` (note the 5 broken lines in `events.jsonl`). |
| 5–22 | Part 1: per-delivery state dict, signing over raw bytes, response handling, audit lines, `skipped_lines`, `delivery()`, tests. Reveal `PART2.md` once delivered-once + audit work. |
| 22–30 | Part 2: retry classification, backoff with jitter, Retry-After, `next_attempt_at <= now` gating, dead after `max_attempts`. |
| ~30 | **Drop the mid-part change** (below), once the classification table is coded. |
| 30–40 | Change + Part 2 tests (scripted receiver, `clock.set(next_attempt_at)`). Reveal `PART3.md`. |
| 40–54 | Part 3: persist after every attempt (atomic), load in the constructor, restart / crash tests. |
| 54–60 | Follow-up discussion (pick 1–2 of the questions below). |

If the candidate is behind at minute 25, reveal Part 2 anyway; `skipped_lines` and the audit
`ts` can wait. If they are behind at minute 45, skip Part 3 code and discuss the design only:
what file, when written, how written, what happens on a crash.

### 30-minute mode (Part 1 plus the start of Part 2)

| min | what happens |
|---|---|
| 0–4 | Hand over `PART1.md`; let them skim the repo. |
| 4–18 | Delivery state, signed POST, 2xx check, audit log, `delivery()`. `skipped_lines` if time allows. |
| 18–20 | Reveal `PART2.md`. Skip the mid-part change. |
| 20–27 | Classification table + `next_attempt_at` scheduling + dead-lettering, ideally with one test. |
| 27–30 | One follow-up question (#1 below). |

Score Part 3 categories as "not observed"; run `test_part1.py` and `test_part2.py -m "not change"`.

## Mid-part requirement change (Part 2, ~minute 30)

Say, verbatim:

> "We just heard from support: some subscribers are slow. Every request must use a
> 5-second timeout, and a timeout (`httpx.TimeoutException`) is retryable, just like
> a 5xx."

What it tests: PART2's table makes "any other `httpx.HTTPError`" permanent, so a timeout is
dead before the change. The change needs (a) passing `timeout=self.timeout_s` on the request
(the injected client has a 60 s default in the tests, so relying on the client default fails),
and (b) adding `httpx.TimeoutException` to the retryable errors. A candidate who wrote the
classification as one small function or table makes it a 2-line change. Good follow-up: "the
receiver's `timeout` script still *records* the request. What does that mean for duplicates?"
(The subscriber may have processed it, which leads into at-least-once and Part 3.)

Hidden tests (marker `change`): `test_part2.py::test_every_request_uses_a_5_second_timeout`,
`::test_timeout_is_retryable`, `::test_timeouts_count_towards_max_attempts`.
No other hidden test scripts a timeout.

## Planted bugs

None. The starter's gaps are honest TODOs (no state, response ignored, `json=` re-serializes,
bad lines silently dropped, `max_attempts`/`timeout_s` unused), not bugs.

## Hint ladder

Give the lowest hint that unblocks; note each hint in the rubric.

**Part 1**
1. "What is the unit of work here: an event, or something else?" (an (event, subscription) pair,
   keyed by both ids)
2. "The receiver says the signature is invalid. Print the bytes you signed and `request.content`.
   Are they the same?" (`json=` re-serializes; sign and send one `body`; also `int(clock.time())`,
   not `time.time()`)
3. "Split it: `_send(event, sub) -> result`, then one place that records the result into the
   delivery state and the audit log."

**Part 2**
1. "Where does the waiting happen?" (nowhere: store `next_attempt_at`; `dispatch_due` skips
   what isn't due)
2. "Write the classification as a function from a response or exception to retry/dead. Then
   `max_attempts` is one `if` on top."
3. "Test it with `receiver.script_event(id, [500, 500, 200])` and `clock.set(d['next_attempt_at'])`."

**Part 3**
1. "If the process is killed right now, what is on disk? What will the next process do?"
2. "How do you make a file write all-or-nothing?" (temp file in the same dir, fsync, `os.replace`;
   or a sqlite transaction)
3. "When exactly do you save: end of the run, or after each attempt? Which one loses work on a crash?"

## Common pitfalls (what the hidden tests catch)

* Signing `json.dumps(event)` but sending `json=event` (different bytes), or signing with
  `time.time()` instead of the clock: `signature_valid` is False.
* Re-sending delivered events on every call (state keyed by event only, or not consulted).
* Keying state by event id only, so one subscriber's success marks the event delivered for all.
* Letting `httpx.ConnectError` escape `dispatch_due()` (Part 1) and abort the whole pass.
* Off-by-one in `skipped_lines` (0-based, or counting blank lines as skipped); missing the
  duplicate-id rule; "last occurrence wins".
* `time.sleep`/`clock.sleep` inside `dispatch_due` for backoff, instead of scheduling.
* Backoff off by one power (`2 ** n` instead of `2 ** (n - 1)`), or jitter applied as `± 50 %`.
* Retry-After capped at 300 or added on top of backoff; 429 not counted as an attempt.
* Retrying a delivery twice in one call when `Retry-After: 0` makes it due again immediately.
* Treating 4xx as retryable, or 408/429 as permanent; the max-attempts failure audited as `failed` instead of `dead`.
* Saving state only at the end of `dispatch_due()`: a crash mid-run re-sends everything
  already delivered in that run (`test_crash_propagates...`, `test_killed_between_send_and_save...`).
* Catching `Exception` around the send: a crash is recorded as a failed attempt instead of propagating.
* Loading state lazily in `dispatch_due()`, so `delivery()` on a fresh instance raises `KeyError`.
* Truncating `audit.jsonl` (opening with `"w"`) on start-up.
* Not hidden-tested but worth raising: a corrupt state file silently treated as "no state"
  (re-sends the entire history); a torn final line in `events.jsonl` while the producer is
  mid-append (reported as skipped once, then delivered on the next pass when complete).

## Follow-up questions

**1. "Can we guarantee exactly-once delivery? What should subscribers do?"**
A strong answer covers: exactly-once over an unreliable network is impossible from the sender
alone. A timeout or a crash after send leaves the outcome unknown, so the honest guarantee is
at-least-once, plus *effectively-once* through receiver-side idempotency: dedupe on `X-Event-Id`
(a unique constraint, or a processed-ids table with a TTL longer than the retry horizon).
Signatures with a timestamp plus a tolerance window stop replay attacks, not duplicates. Shrink
the duplicate window by saving an "in-flight" marker before sending, so restarts can be
reported. Document the contract publicly (Stripe/GitHub do). Ordering is not guaranteed either,
because retries reorder events, so subscribers should use `created_at` or a per-resource
version and not assume arrival order.

**2. "One subscriber takes the full 5 s timeout on every request. What happens to everyone else, and how do you fix it?"**
Strong: with a sequential loop, every slow request delays all deliveries behind it (head-of-line
blocking); 1,000 queued events × 5 s is 83 minutes of lag for *other* customers. Fixes: per-subscription
queues and workers (or async with a per-subscription concurrency cap), so one tenant's slowness
is isolated. A circuit breaker per endpoint: after N consecutive failures, stop sending for a
cool-off period and probe with one request. Shorter connect timeouts than read timeouts.
Auto-disable chronically dead endpoints and notify the customer. Bounded retries so dead
endpoints don't eat capacity forever. Metrics per subscription: success rate, p99 latency,
backlog age.

**3. "Event volume grows 100x. What breaks first and what replaces it?"**
Strong: re-reading the entire events file on every pass is O(total history). Keep a durable read
offset or cursor instead, or have producers write to a queue (Kafka/SQS) or an outbox table in
the same transaction as the business change (transactional outbox). Rewriting one JSON state
file per attempt is O(deliveries) per attempt. Move to SQLite/Postgres rows with an index on
`(status, next_attempt_at)`, and claim due work with `SELECT ... FOR UPDATE SKIP LOCKED` or leases
so several dispatcher processes can run. Partition by subscription id to keep per-subscription
ordering (if promised) while scaling out. Archive delivered rows. Rotate and ship the audit log.
Backpressure, plus a dead-letter queue with a replay tool. Fsync cost: batch commits.

## Reference solution

`reference/dispatcher/`:
* `events.py`: `EventStore.scan()` returns events plus `skipped_lines` (duplicate ids skipped; `read()` kept).
* `dispatcher.py`: `_send()` builds one body, signs it, and turns httpx errors into an `AttemptResult`
  (non-httpx exceptions propagate). `_attempt()` applies the policy, appends the audit line, then saves state.
* `policy.py`: retryable statuses/errors, `parse_retry_after`, `Backoff` (`min(300, 10·2^(n-1)) · U[0.5, 1]`).
* `state.py`: `DeliveryStore` (one JSON file, temp + fsync + `os.replace`; an unreadable file
  raises `StateError` rather than starting over) and `AuditLog` (append + fsync).
* `__main__.py`: unchanged except exit code 2 on unreadable state.

The constructor takes one extra optional keyword, `rng: random.Random | None`, for deterministic
jitter in tests. The hidden tests never pass it.

Lines a candidate must add (reference minus starter, excluding tests/comments/blanks): ≈184 in
total. Part 1 ≈ 85 (send/record/delivery/report ≈ 55, `scan` + duplicates ≈ 22, audit ≈ 8),
Part 2 ≈ 45 (policy ≈ 26, scheduling branches ≈ 15, change ≈ 3), Part 3 ≈ 55 (store + atomic
write ≈ 40, load in constructor, CLI ≈ 6) plus discussion.

Manual run (two terminals, from `candidate/` or `reference/`):

```bash
python -m mock_services.webhook_server --port 9100 --secret whsec_qa_bot_41d0 --fail-first 2
python -m dispatcher run --once --state-dir /tmp/p5state --events data/events.jsonl --subscriptions data/subscriptions.json
# reference: {"attempted": 11, "delivered": 9, "failed": 2, "dead": 0, "skipped_lines": [3, 7, 8, 9, 11]}
```
