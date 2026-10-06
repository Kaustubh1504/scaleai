"""A fake worker node for load balancer and scheduler problems.

States
------
healthy  processes tasks after ``latency_s``; heartbeats normally.
slow     like healthy but latency is multiplied by ``slow_factor``.
silent   stops heartbeating and hangs on every request until the caller's
         timeout (or ``hang_s``), then raises ``WorkerTimeoutError``.
dead     heartbeats stop; every request raises ``WorkerUnreachableError``.

A worker at ``capacity`` in-flight tasks rejects new ones with
``WorkerOverloadedError``. ``crash_on_next()`` makes the next accepted task
die mid-flight (the task is lost and the worker becomes dead), which is the
classic failover scenario; ``crash_if=predicate`` does the same for every task
matching it (a poison job). Both raise ``WorkerCrashedError``, a subclass of
``WorkerUnreachableError``, so callers can tell "died mid-task" from "was already down".
"""

from __future__ import annotations

import threading
from enum import Enum
from typing import Any, Callable

from ..fake_clock import Clock, RealClock, aelapse, elapse


class WorkerState(str, Enum):
    HEALTHY = "healthy"
    SLOW = "slow"
    SILENT = "silent"
    DEAD = "dead"


class WorkerError(Exception):
    def __init__(self, worker_id: str, message: str):
        super().__init__(f"worker {worker_id}: {message}")
        self.worker_id = worker_id


class WorkerUnreachableError(WorkerError):
    """Connection refused or dropped. The task did not complete."""


class WorkerCrashedError(WorkerUnreachableError):
    """The connection dropped mid-task: the worker accepted the task and then died."""


class WorkerTimeoutError(WorkerError):
    """No response within the timeout. The task may or may not have run."""


class WorkerOverloadedError(WorkerError):
    """The worker rejected the task because it is at capacity (HTTP 503)."""


class TaskFailedError(WorkerError):
    """The task itself raised an error on the worker (HTTP 500)."""


def default_handler(worker_id: str, task: Any) -> dict:
    task_id = task.get("id") if isinstance(task, dict) else task
    return {"task_id": task_id, "worker_id": worker_id, "status": "done"}


class MockWorker:
    def __init__(
        self,
        worker_id: str,
        *,
        capacity: int = 4,
        latency_s: float = 0.0,
        clock: Clock | None = None,
        handler: Callable[[str, Any], Any] | None = None,
        hang_s: float = 30.0,
        crash_if: Callable[[Any], bool] | None = None,
    ):
        self.worker_id = worker_id
        self.capacity = capacity
        self.latency_s = latency_s
        self.clock = clock or RealClock()
        self.handler = handler or default_handler
        self.hang_s = hang_s
        self.crash_if = crash_if  # a "poison" predicate: matching tasks kill the worker mid-flight
        self.state = WorkerState.HEALTHY
        self.slow_factor = 1.0
        self.in_flight = 0
        self.received: list[Any] = []  # every task that reached the worker
        self.completed: list[Any] = []  # tasks that finished successfully
        self._crash_next = False
        self._die_after: int | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------- controls

    def kill(self) -> None:
        self.state = WorkerState.DEAD

    def revive(self) -> None:
        self.state = WorkerState.HEALTHY
        self.slow_factor = 1.0
        self._crash_next = False
        self._die_after = None

    def slow(self, factor: float = 10.0) -> None:
        self.state = WorkerState.SLOW
        self.slow_factor = factor

    def go_silent(self) -> None:
        self.state = WorkerState.SILENT

    def crash_on_next(self) -> None:
        """The next accepted task is lost mid-flight and the worker dies."""
        self._crash_next = True

    def die_after(self, n_tasks: int) -> None:
        """Complete ``n_tasks`` more tasks, then die."""
        self._die_after = n_tasks

    @property
    def alive(self) -> bool:
        return self.state not in (WorkerState.DEAD, WorkerState.SILENT)

    # ------------------------------------------------------------- behaviour

    def heartbeat(self) -> dict | None:
        """The heartbeat payload, or None if this worker would not send one."""
        if not self.alive:
            return None
        with self._lock:
            return {
                "worker_id": self.worker_id,
                "in_flight": self.in_flight,
                "capacity": self.capacity,
                "ts": self.clock.time(),
            }

    def _admit(self, task: Any, timeout: float | None) -> float:
        """Accept the task or raise. Returns the latency to wait."""
        if self.state is WorkerState.DEAD:
            raise WorkerUnreachableError(self.worker_id, "connection refused")
        if self.state is WorkerState.SILENT:
            return -1.0
        with self._lock:
            if self.in_flight >= self.capacity:
                raise WorkerOverloadedError(self.worker_id, f"at capacity ({self.capacity})")
            self.in_flight += 1
            self.received.append(task)
        return self.latency_s * self.slow_factor

    def _finish(self, task: Any, latency: float, timeout: float | None) -> Any:
        try:
            if self._crash_next or (self.crash_if is not None and self.crash_if(task)):
                self._crash_next = False
                self.state = WorkerState.DEAD
                raise WorkerCrashedError(self.worker_id, "connection dropped mid-task")
            if timeout is not None and latency > timeout:
                raise WorkerTimeoutError(self.worker_id, f"no response within {timeout:g}s")
            try:
                result = self.handler(self.worker_id, task)
            except Exception as exc:  # noqa: BLE001 - surfaced to the caller as a task failure
                raise TaskFailedError(self.worker_id, f"task failed: {exc}") from exc
            with self._lock:
                self.completed.append(task)
                if self._die_after is not None:
                    self._die_after -= 1
                    if self._die_after <= 0:
                        self._die_after = None
                        self.state = WorkerState.DEAD
            return result
        finally:
            with self._lock:
                self.in_flight -= 1

    def process(self, task: Any, timeout: float | None = None) -> Any:
        latency = self._admit(task, timeout)
        if latency < 0:  # silent
            elapse(self.clock, timeout if timeout is not None else self.hang_s)
            raise WorkerTimeoutError(self.worker_id, "no response")
        elapse(self.clock, min(latency, timeout) if timeout is not None else latency)
        return self._finish(task, latency, timeout)

    async def aprocess(self, task: Any, timeout: float | None = None) -> Any:
        latency = self._admit(task, timeout)
        if latency < 0:
            await aelapse(self.clock, timeout if timeout is not None else self.hang_s)
            raise WorkerTimeoutError(self.worker_id, "no response")
        await aelapse(self.clock, min(latency, timeout) if timeout is not None else latency)
        return self._finish(task, latency, timeout)

    def __repr__(self) -> str:
        return f"MockWorker({self.worker_id!r}, state={self.state.value}, in_flight={self.in_flight})"


class WorkerFleet:
    """Holds workers and drives their heartbeats on a clock.

        fleet = WorkerFleet([MockWorker("w1", clock=clock)], clock=clock, interval_s=1.0)
        fleet.run(5.0, sink=balancer.on_heartbeat)   # 5 ticks, 1 heartbeat per live worker per tick
    """

    def __init__(self, workers: list[MockWorker] | None = None, *, clock: Clock | None = None,
                 interval_s: float = 1.0):
        self.clock = clock or RealClock()
        self.interval_s = interval_s
        self.workers: dict[str, MockWorker] = {w.worker_id: w for w in workers or []}

    def add(self, worker: MockWorker) -> MockWorker:
        self.workers[worker.worker_id] = worker
        return worker

    def remove(self, worker_id: str) -> None:
        self.workers.pop(worker_id, None)

    def __getitem__(self, worker_id: str) -> MockWorker:
        return self.workers[worker_id]

    def __iter__(self):
        return iter(list(self.workers.values()))

    def emit_heartbeats(self, sink: Callable[[dict], Any]) -> int:
        sent = 0
        for worker in self:
            payload = worker.heartbeat()
            if payload is not None:
                sink(payload)
                sent += 1
        return sent

    def run(self, seconds: float, sink: Callable[[dict], Any]) -> None:
        """Advance the clock in ``interval_s`` steps, emitting heartbeats after each step."""
        steps = int(round(seconds / self.interval_s))
        for _ in range(steps):
            elapse(self.clock, self.interval_s)
            self.emit_heartbeats(sink)
