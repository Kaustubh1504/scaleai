# Part 2: Heartbeats and failover (about 20 minutes)

Workers crash, hang and restart, and new ones join while the pool is running.
Detect workers that are gone, move their jobs elsewhere, and take them back
when they recover.

## Contract (keep these signatures)

```python
pool.add_worker(worker) -> None
pool.on_heartbeat(payload: dict) -> None
```

A heartbeat looks like `MockWorker.heartbeat()` output:

```python
{"worker_id": "w1", "in_flight": 0, "capacity": 4, "ts": 1700000000.0}
```

`WorkerFleet(workers, clock=clock).run(seconds, sink=pool.on_heartbeat)` moves
the clock forward one second at a time and delivers one heartbeat per live
worker per second. Killed and silent workers send none.

## Joining: `add_worker(worker)`

Works at any time, including between rounds. The worker is registered after
the existing ones, starts **up**, and counts as last heard from at
`clock.time()`. Its count of earlier `process()` calls starts at 0, so the
least-loaded rule favours it. A `worker_id` that is already registered raises
`ValueError` and leaves the registered worker unchanged.

## Up and down

A worker is **down** when either:

* it has not been heard from for **more than** `heartbeat_timeout_s` seconds
  (`clock.time() - last_heard > heartbeat_timeout_s`), where "heard from"
  means registered or sent a valid heartbeat; or
* a `process()` call to it failed with `WorkerUnreachableError` or
  `WorkerTimeoutError` (below), and it has not sent a valid heartbeat since.

Otherwise it is **up**. Down workers get no jobs. `status()` reports the state
at the current `clock.time()`; nothing runs in the background.

## `on_heartbeat(payload)`

* Ignore it (no exception, no state change) if `payload` is not a dict, its
  `worker_id` is missing or not a string, or no worker with that id is
  registered. Other fields are not checked.
* Otherwise the worker is heard from at `clock.time()`. Use the pool's clock,
  not the payload's `ts`: worker clocks can be wrong. A down worker that sends
  a valid heartbeat is **up** again right away.

## Failover

During the run phase, when `process()` raises:

| error | job | worker |
|---|---|---|
| `WorkerUnreachableError` or `WorkerTimeoutError` | goes back to the queue (failover) | **down** |
| `WorkerOverloadedError` | goes back to the queue (failover) | stays up |
| `TaskFailedError` | as in Part 1 | stays up |

After one of the first two rows, the pool sends nothing more to that worker
for the rest of the round. Its other jobs planned in this round are **not
sent**: they go back to the queue too, without an attempt.

Jobs that go back to the queue are not re-planned in the same round. At the
end of the round they are put at the **front** of the queue, ahead of every
job that was not planned, in the order they were planned. A failover never
marks a job failed: it is retried in a later round, on whichever worker the
least-loaded rule picks. `attempts` still counts every `process()` call.

Any other exception propagates unchanged.

### Example

Workers `w1`, `w2`, `concurrency_per_worker=2`, queue `a b c d e`. `w1`
crashes on its first job (`w1.crash_on_next()`):

| round | sent | outcome | `pending()` after |
|---|---|---|---|
| 1 | a→w1, b→w2, d→w2 (c, planned on w1, is not sent) | a lost, w1 down; b, d done | `["a", "c", "e"]` |
| 2 | a→w2, c→w2 | done | `["e"]` |

## Constraints

* Everything from Part 1 still holds.
* Write tests. Drive heartbeats with `WorkerFleet.run(...)` or by calling
  `on_heartbeat` directly, and move time with `FakeClock.advance()` / `set()`.
  `kill()`, `go_silent()`, `slow()`, `crash_on_next()` and `revive()` on a
  `MockWorker` give you every failure.
