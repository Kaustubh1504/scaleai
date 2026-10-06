# Part 2: Heartbeats (about 20 minutes)

Failing over only when a dispatch hits a dead worker is too late, and right
now an `UNREACHABLE` worker never comes back. Workers send heartbeats; use
them to detect silent workers early and to bring recovered workers back.

## Contract (keep these signatures)

```python
lb.on_heartbeat(payload: dict) -> None
lb.check_health() -> None
```

A heartbeat looks like `MockWorker.heartbeat()` output:

```python
{"worker_id": "w1", "in_flight": 2, "capacity": 4, "ts": 1700000000.0}
```

`WorkerFleet(workers, clock=clock).run(seconds, sink=lb.on_heartbeat)` moves
the clock forward one second at a time and delivers one heartbeat per live
worker per second. Killed and silent workers send none.

## `on_heartbeat(payload)`

* Ignore the heartbeat (no exception, no state change) if it is malformed or
  if its `worker_id` is not registered. Malformed means: not a dict;
  `worker_id` missing or not a string; `in_flight` or `capacity` missing or
  not an integer; `in_flight < 0`; or `capacity < 1`. Ignore extra keys.
* Otherwise record the worker as last seen at `clock.time()`. Use the
  balancer's clock, not the payload's `ts`, because worker clocks can be
  wrong. Also record the reported `in_flight` and `capacity`.
* Then set the worker's state from the reported load. This applies whatever
  state the worker was in, including `UNREACHABLE`:
  * `in_flight >= capacity`: `OVERLOADED`, with the cooldown from Part 1
    starting now. It becomes `ACTIVE` again after `overload_cooldown_s`, or
    sooner if a later heartbeat reports less load.
  * `in_flight < capacity`: `ACTIVE`, right away, even if an overload
    cooldown has not passed yet.

## `check_health()`

Marks every worker whose last-seen time is **more than**
`heartbeat_timeout_s` seconds before `clock.time()` as `UNREACHABLE`. A
worker that has never sent a valid heartbeat counts as last seen when it was
registered. `check_health()` never makes a worker `ACTIVE`; only a heartbeat
does that.

Only valid heartbeats from registered workers update last-seen. A successful
dispatch does not. `dispatch()` does not call `check_health()` itself:
whoever runs the balancer calls it periodically.

## Constraints

* Everything from Part 1 still holds.
* Write tests. Drive heartbeats with `WorkerFleet.run(...)` or by calling
  `on_heartbeat` directly, and move time with `FakeClock.advance()` / `set()`.
