"""The worker nodes the pool keeps busy (in-process fakes).

    from mock_services.workers import MockWorker, WorkerFleet
    w = MockWorker("w1", capacity=4, latency_s=0.0, clock=clock)
    w.process(payload, timeout=2.0)  # -> result, or raises one of the errors below
    w.heartbeat()                     # -> {"worker_id", "in_flight", "capacity", "ts"}, or None if it is down
    w.kill(); w.go_silent(); w.slow(10); w.crash_on_next(); w.revive()
    w.received                        # every payload that reached the worker

    fleet = WorkerFleet([w], clock=clock, interval_s=1.0)
    fleet.run(5, sink=pool.on_heartbeat)  # advance 5 s; one heartbeat per live worker per second
    fleet.emit_heartbeats(pool.on_heartbeat)  # one heartbeat per live worker, without moving the clock

Errors raised by process() (all subclass WorkerError):
    WorkerOverloadedError   at capacity; the job was rejected and did not run
    WorkerUnreachableError  connection refused or dropped; the job did not complete
    WorkerTimeoutError      no answer within ``timeout``; the job may or may not have run
    TaskFailedError         the job itself raised on the worker (a bug in the job, bad input, ...)

A killed or silent worker sends no heartbeats. A silent or too-slow worker
hangs until ``timeout``, which moves a FakeClock forward by that much.
Test tip: ``w.in_flight = w.capacity`` makes a worker reject jobs as overloaded.

``handler=`` decides what a worker does with a payload (default: return
{"task_id", "worker_id", "status": "done"}); if it raises, process() raises
TaskFailedError. ``CrashingWorker`` below additionally dies mid-job on a
payload marked ``"crash": true``: the classic poison job.

Details: ../../shared/README.md (mock_worker).
"""

from __future__ import annotations

from typing import Any

import mock_services  # noqa: F401  (puts shared/ on sys.path)
from shared.mock_worker import (
    MockWorker,
    TaskFailedError,
    WorkerError,
    WorkerFleet,
    WorkerOverloadedError,
    WorkerTimeoutError,
    WorkerUnreachableError,
    default_handler,
)

__all__ = [
    "CrashingWorker", "MockWorker", "TaskFailedError", "WorkerError", "WorkerFleet", "WorkerOverloadedError",
    "WorkerTimeoutError", "WorkerUnreachableError", "default_handler",
]


class CrashingWorker(MockWorker):
    """A MockWorker that dies mid-job (WorkerUnreachableError, then dead) on payloads with ``"crash": true``."""

    def process(self, task: Any, timeout: float | None = None) -> Any:
        if isinstance(task, dict) and task.get("crash"):
            self.crash_on_next()
        return super().process(task, timeout)
