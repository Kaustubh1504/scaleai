"""The worker nodes this balancer routes to (in-process fakes).

    from mock_services.workers import MockWorker, WorkerFleet
    w = MockWorker("w1", capacity=4, latency_s=0.0, clock=clock)
    w.process(payload, timeout=2.0)  # -> result, or raises one of the errors below
    w.heartbeat()                     # -> {"worker_id", "in_flight", "capacity", "ts"}, or None if it is down
    w.kill(); w.go_silent(); w.slow(10); w.crash_on_next(); w.revive()

    fleet = WorkerFleet([w], clock=clock, interval_s=1.0)
    fleet.run(5, sink=balancer.on_heartbeat)  # advance 5 s; one heartbeat per live worker per second

Errors raised by process() (all subclass WorkerError):
    WorkerOverloadedError   at capacity; the task was rejected and did not run
    WorkerUnreachableError  connection refused or dropped; the task did not complete
    WorkerTimeoutError      no answer within ``timeout``; the task may or may not have run
    TaskFailedError         the task itself raised on the worker; retrying elsewhere will not help

A killed or silent worker sends no heartbeats. Test tip: ``w.in_flight = w.capacity``
makes a worker reject new tasks as overloaded. Details: ../../shared/README.md (mock_worker).
"""

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
    "MockWorker", "TaskFailedError", "WorkerError", "WorkerFleet", "WorkerOverloadedError",
    "WorkerTimeoutError", "WorkerUnreachableError", "default_handler",
]
