# prob-007 — Worker Pool with Failover and DLQ (interviewer notes)

**Mimics:** a close variant of the reported real "lightweight load balancer"
round (worker states, heartbeats, dynamic joining, failover). prob-002 is a
synchronous router: `dispatch(task)` returns a result. This problem is a
**job-processing pool** instead: a coordinator owns the queue, keeps a fleet
busy in rounds, moves a dead worker's jobs elsewhere, retries with backoff on
the clock, and dead-letters jobs that keep failing or keep killing workers.
**Difficulty:** medium · **Mode:** plain Python (no web framework) · **Starter:** minimal skeleton (`pool/coordinator.py` stubs + a demo driver) · **Planted bugs:** none

## Setup

```bash
python tools/export_candidate.py prob-007 ~/interview --part1-only   # give the candidate prob-007/
# afterwards, from scale-backend-sets/:
SOLUTION_DIR=~/interview/prob-007 python -m pytest prob-007/interviewer/hidden_tests -q
SOLUTION_DIR=... python -m pytest prob-007/interviewer/hidden_tests -m "not change"   # pinned jobs not delivered
```

The hidden tests build `Pool([...], FakeClock(start=1000), ...)` with
`shared.mock_worker.MockWorker` (and a copy of `CrashingWorker` in
`hidden_tests/conftest.py`), not the candidate's `mock_services`. They drive
heartbeats with `WorkerFleet.run()` or direct `on_heartbeat()` calls.
Everything is single-threaded and deterministic. Tests touch only the
public contract in PART1–3 (`pool.coordinator.Pool`). If the candidate moved
`Pool`, re-export it in a scratch copy rather than failing them outright.

## The model, in one paragraph (so you can answer questions fast)

`tick()` is one **round**: *plan* (walk the queue; give each eligible job to
the least-loaded up worker with a free slot: fewest jobs this round, then
fewest `process()` calls ever, then registration order; jobs that can't be
placed stay put), then *run* (send planned jobs one by one in plan order).
`process()` is a blocking call, so a worker's "in-flight jobs" are the ones
planned on it in the current round. When a send hits
`WorkerUnreachableError`/`WorkerTimeoutError`, the worker is down until its
next heartbeat, and that job plus the worker's unsent jobs go to the **front**
of the queue in plan order. `WorkerOverloadedError` does the same, but the
worker stays up. Staleness (`now - last_heard > heartbeat_timeout_s`) is
computed lazily from the clock. Part 3: `TaskFailedError` → back of the queue
with backoff `base * 2**(n-1)` (only these count toward `max_attempts`); lost
on 2 different workers → DLQ `"poison"`; `drain()` closes intake, runs what
it can, and hands back what's left.

Candidates often ask "why not threads?". Answer: the round model makes every
rule testable on a fake clock. In production the run phase would be
concurrent RPCs, and that's follow-up material.

## Timeline

### 60-minute mode

| min | what happens |
|---|---|
| 0–3 | Hand over `PART1.md`. Candidate reads `pool/coordinator.py`, `mock_services/workers.py`, glances at `data/jobs.jsonl` and `pool/demo.py`. |
| 3–20 | Part 1: job records, submit idempotency, the plan/run round, least-loaded key, `job()`/`pending()`/`status()`/`results`, tests. Check they reproduce the PART1 example table. |
| ~20 | Reveal `PART2.md` once a round runs end to end (inspection edge cases can trail). |
| 20–38 | Part 2: up/down predicate, `on_heartbeat`, failover branches, front-of-queue requeue, `add_worker`, tests with `crash_on_next()` and `WorkerFleet`. |
| ~30 | **Drop the mid-part change** (below), once the crash example from PART2 passes. |
| ~38 | Reveal `PART3.md`. |
| 38–54 | Part 3: failure count + backoff eligibility, `dead_letters` with history, poison rule, `drain()`. Ask them to run `python -m pool.demo`. |
| 54–60 | Discussion prompts from PART3 / follow-ups below (pick 1–2). |

If the candidate is behind at minute 25, reveal Part 2 anyway. If they are
behind at minute 45, have them implement backoff + `max_attempts` only, and
describe poison and drain in words.

### 30-minute mode (Part 1 plus the start of Part 2)

| min | what happens |
|---|---|
| 0–2 | Hand over `PART1.md`. |
| 2–17 | Part 1: submit, the round, least-loaded, inspection, at least one test of the example table. |
| 17–18 | Reveal `PART2.md`. Skip the mid-part change. |
| 18–27 | Failover on `crash_on_next()` with the front-of-queue rule, and heartbeat staleness with one `WorkerFleet` test. |
| 27–30 | Follow-up #1 (duplicate side effects after a timeout). |

Score Part 3 categories as "not observed". Run `test_part1.py` and
`test_part2.py -m "not change"`.

## Mid-part requirement change (Part 2, ~minute 30)

Say, verbatim:

> "Some jobs read a big local cache that only one machine has. Add an optional
> keyword argument: `submit(job_id, payload, pinned_worker="w2")`. A pinned job
> may only run on that worker. If that worker is down, already full this
> round, or not registered yet, the job waits where it is in the queue, and
> the jobs behind it are still planned as usual. If its worker dies while
> running it, it fails over to the front like any other job and keeps
> waiting for that worker. Unpinned jobs don't change."

What it tests: whether "which workers may take this job" is one predicate in
the plan phase or tangled into the least-loaded `min()`, and whether the
walk `continue`s or `break`s on an unplaceable job. Before the change the two
are equivalent (if one unpinned job doesn't fit, none does), so a `break` is
not wrong in Part 1, but it is now. Also whether pinning survives failover
(the pin lives on the job record, not in the queue). Strong candidates ask
whether a pinned job counts toward idempotency (the reference compares the
payload only; either answer is fine, and no test checks it).
Hidden tests: the five `test_part2.py::test_pinned_*` tests (marker `change`).
Non-change tests never pass `pinned_worker`.

## Planted bugs

None. This is a skeleton problem. The starter already validates the
constructor and provides `run_until_idle()` and the demo driver.

## Hint ladder

Give the lowest hint that unblocks; note each hint in the rubric.

**Part 1**
1. "What do you need to remember per job and per worker? Write those two records first." (status, attempts, worker, result, error / registration seq, calls made)
2. "Can you write the least-loaded choice as a single `min()` with a tuple key?" (`(load_this_round, calls_so_far, seq)`)
3. "Split `tick()` into `plan()` returning `[(job, worker)]` and a loop that sends them. Rebuild the queue once at the end."

**Part 2**
1. "Run `crash_on_next()` on `w1` with the PART2 example and print `pending()` after each round. Which jobs should be where?"
2. "Is 'down' a state you store, or something you can compute from last-heard time and a flag?" (lazy `is_up(now)`; nothing runs in the background)
3. "During the run loop, keep a set of workers that failed this round, and a `front` list. What goes in it when you skip a job?"

**Part 3**
1. "Where does a job wait during its backoff? Does it need to leave the queue?" (no: a `not_before` timestamp, skipped by the plan phase)
2. "Which errors are the job's fault, and which are the worker's? Which should count toward `max_attempts`?"
3. "For poison, what do you need to remember per job?" (a set of worker ids it was lost on, not a counter)

## Common pitfalls (what the hidden tests catch)

* Least-loaded by *this round only*, so a single job per round always goes to `w1` (`test_least_loaded_spreads_single_jobs_across_rounds`).
* Counting "calls so far" including the current round's plan, or ignoring registration order on ties (`test_tie_break_on_earlier_calls_within_a_round`).
* Stopping the walk at the first job that cannot be placed. Fine before the change; wrong for pinned jobs and for jobs in backoff (`test_waiting_job_keeps_its_place_and_does_not_block`).
* Storing the caller's payload object (`test_caller_mutating_payload_does_not_change_job`), or treating a done job's id as reusable.
* Re-planning failed-over jobs in the same round, or appending them to the back (`test_spec_example_crash_fails_over_to_the_front`, `test_failover_order_with_two_failing_workers`).
* Still sending the dead worker's other planned jobs in the same round (each would hang or be refused); or forgetting to requeue them.
* Marking the worker down on `WorkerOverloadedError`, or on `TaskFailedError`.
* Staleness from the payload's `ts`; `>=` instead of `>`; ignored heartbeats still refreshing last-heard; heartbeat from an unknown id raising `KeyError`.
* A worker that failed a send coming back *without* a heartbeat because its last-heard is still fresh (`test_down_after_failure_until_next_heartbeat`).
* Backoff computed from the time *before* the call (`test_backoff_is_measured_from_after_the_failed_call`), off-by-one in the exponent, `>` vs `>=` at the eligibility boundary, or `clock.sleep()` in the pool.
* Counting worker losses or overload refusals toward `max_attempts`; applying backoff to failovers.
* Poison counted as "lost twice" instead of "lost on two different workers" (`test_lost_twice_on_same_worker_is_not_poison`); blaming the unsent jobs on a dying worker.
* Returning internal lists from `dead_letters` / `results` / `job()` (tests mutate the returned objects).
* `drain()` that waits (sleeps) for backoffs, dead-letters leftovers, or still accepts duplicate submits.
* Not something the hidden tests check, but worth raising: `copy.deepcopy` of a non-copyable payload; logging every state transition; the unbounded flapping of a slow-but-heartbeating worker (only bounded once it's lost on a second worker).

## Follow-up questions

**1. "A worker times out *after* it finished the job, and we ran it again on another worker. What did the outside world see, and how do you make that safe?"**
A strong answer covers: the pool gives **at-least-once** execution. A timeout
is ambiguous (the mock says "may or may not have run"), and so is a crash
after the side effect but before the reply. So the job ran twice: two emails,
two charges, two writes. Fixes:
* make handlers idempotent: pass an idempotency key (`job_id`, not `job_id + attempt`) and have the side-effecting service dedupe on it with a TTL store, or use conditional writes/upserts keyed by job id;
* separate "never started" errors (connection refused, overloaded), which are safe to retry, from ambiguous ones (timeout, dropped mid-task);
* for non-idempotent work, fence with a lease/epoch so a late finisher's result is rejected (the attempt number is the fencing token);
* record the first result and drop later duplicates in `results`.
Exactly-once is achieved end to end, not by the queue.

**2. "An operator fixes the bug behind 5,000 dead-lettered jobs. Design the replay tool."**
Strong:
* The DLQ must be durable and carry enough to replay: the payload as submitted, the reason, the per-attempt history, and the code/version that failed.
* Replay is a deliberate, filtered action: by reason, error signature, time window or tenant, with a dry run that shows counts first.
* Replayed jobs get a fresh attempt budget but **keep their idempotency key**, so already-applied side effects dedupe.
* Rate-limit the replay and push it through the normal queue at low priority, so it can't starve live traffic or re-kill the fleet (poison jobs go to a canary worker first).
* Mark each DLQ entry `replayed` with a link to the new attempt, so a second replay doesn't double-run it.
* Alert on DLQ growth rate and on the poison reason specifically; group by error signature so one bug is one ticket.
* Discuss retention, and PII in payloads.

**3. "This coordinator holds the queue in memory in one process. What happens when it crashes, and how do you make it HA and scale it?"**
Strong:
* Today a crash loses every queued job and the DLQ. Persist the queue: a DB table with `status`, `not_before` and `lease_until`, claimed with `SELECT ... FOR UPDATE SKIP LOCKED`, or SQS/Redis Streams/Kafka with visibility timeouts.
* Once state is durable the coordinator is (nearly) stateless. Run several, or flip to a **pull model** where workers claim jobs with leases. A lease timeout then replaces heartbeat failover: an unacked job reappears.
* HA with a single active scheduler needs leader election (etcd/ZooKeeper lease) with fencing tokens, so a paused old leader can't double-assign.
* Backoff becomes the `not_before` column or a delayed queue. The DLQ is a separate durable queue or table.
* Scale by sharding the queue (by tenant or hash), batching claims, and adding per-tenant fairness.
* Watch for thundering-herd re-delivery when many leases expire at once (jitter), and keep `max_attempts` as a delivery count on the durable record so it survives restarts.

## Reference solution

`reference/pool/`:
* `records.py` (new): `JobRecord` (status, attempts, failures, last worker,
  result/error, `not_before`, `lost_on` set, history, pin) with a `view()`,
  and `Member` (worker, registration seq, `last_heard`, `failed` flag, calls
  made) with the lazy `is_up(now, timeout)` predicate.
* `coordinator.py`: `_plan(now)` (one walk; eligibility, pin and slot filter;
  `min()` on `(load, sent, seq)`), `tick()` (one run loop with a `skip` set and
  `front`/`back` lists; the queue is rebuilt once as
  `front + unplanned + back`), and `_send()`, which maps each worker error to
  an outcome (`done`/`failed`/`retry`/`lost`/`refused`). `on_heartbeat`,
  `_dead_letter`, `drain` and copies on every read path round it out.
* `demo.py`: unchanged from the starter. Run it with `python -m pool.demo` (about 0.5 s of real time).

Lines a candidate must add (verifier: 172 total, excluding tests):
Part 1 ≈ 100 (records 40, submit 12, plan + run + send 35, inspection 13),
Part 2 ≈ 35 (up/down predicate 3, failover branches and requeue 17, `add_worker`/`on_heartbeat` 15),
Part 3 ≈ 37 (backoff and failure count 8, poison 4, history + dead letters 12, drain/closed 10, copies 3).
The pinned-job change is about 3 lines.
