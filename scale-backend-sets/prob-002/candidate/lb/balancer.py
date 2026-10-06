"""Routes tasks to workers.

Today this is plain round robin over every registered worker. It does not
track worker health, and any error a worker raises (see
``mock_services/workers.py``) propagates straight to the caller.

Keep the constructor and the public method signatures: other services (and
the interviewer's tests) call them.

Not thread-safe: one thread owns a balancer and calls all of its methods.
"""

from __future__ import annotations

import logging

from lb.models import DispatchResult, Task, Worker, WorkerState
from lb.registry import WorkerRegistry
from mock_services.clock import Clock, RealClock

__all__ = ["DispatchResult", "LoadBalancer", "LoadBalancerError", "NoWorkersAvailable", "TaskFailed"]

log = logging.getLogger("lb")


class LoadBalancerError(Exception):
    """Base class for errors raised by the balancer."""


class NoWorkersAvailable(LoadBalancerError):
    """No worker could take the task."""

    def __init__(self, task_id: str, message: str = "no worker available"):
        super().__init__(f"task {task_id}: {message}")
        self.task_id = task_id


class TaskFailed(LoadBalancerError):
    """The task itself failed on a worker; sending it elsewhere will not help."""

    def __init__(self, task_id: str, worker_id: str, reason: str):
        super().__init__(f"task {task_id} failed on {worker_id}: {reason}")
        self.task_id = task_id
        self.worker_id = worker_id
        self.reason = reason


class LoadBalancer:
    def __init__(
        self,
        clock: Clock | None = None,
        *,
        task_timeout_s: float = 2.0,
        heartbeat_timeout_s: float = 3.0,
        overload_cooldown_s: float = 5.0,
        max_attempts: int = 3,
    ):
        for name, value in (("task_timeout_s", task_timeout_s), ("heartbeat_timeout_s", heartbeat_timeout_s),
                            ("overload_cooldown_s", overload_cooldown_s)):
            if value <= 0:
                raise ValueError(f"{name} must be positive, got {value!r}")
        if max_attempts < 1:
            raise ValueError(f"max_attempts must be at least 1, got {max_attempts!r}")
        self.clock = clock or RealClock()
        self.task_timeout_s = task_timeout_s
        self.heartbeat_timeout_s = heartbeat_timeout_s
        self.overload_cooldown_s = overload_cooldown_s
        self.max_attempts = max_attempts
        self.registry = WorkerRegistry()
        self.failed: list[tuple[Task, str]] = []  # (task, reason) for tasks given up on
        self._next = 0  # round-robin position

    # ------------------------------------------------------------ membership

    def add_worker(self, worker: Worker) -> None:
        self.registry.register(worker)
        log.info("worker %s joined", worker.worker_id)

    def remove_worker(self, worker_id: str) -> None:
        self.registry.unregister(worker_id)
        log.info("worker %s left", worker_id)

    def worker_state(self, worker_id: str) -> WorkerState:
        raise NotImplementedError("worker states are not tracked yet")

    # --------------------------------------------------------------- routing

    def dispatch(self, task: Task) -> DispatchResult:
        """Send ``task`` to the next worker and return its result."""
        workers = list(self.registry)
        if not workers:
            raise NoWorkersAvailable(task.id, "no workers registered")
        worker = workers[self._next % len(workers)]
        self._next += 1
        task.attempts += 1
        result = worker.process(task.payload, timeout=self.task_timeout_s)
        log.debug("task %s handled by %s", task.id, worker.worker_id)
        return DispatchResult(task.id, worker.worker_id, result, task.attempts)

    # ---------------------------------------------------------------- health

    def on_heartbeat(self, payload: dict) -> None:
        raise NotImplementedError("heartbeats are not handled yet")

    def check_health(self) -> None:
        raise NotImplementedError("health checks are not implemented yet")

    # ----------------------------------------------------------------- queue

    def submit(self, task: Task) -> None:
        raise NotImplementedError("the task queue is not implemented yet")

    def drain(self) -> list[DispatchResult]:
        raise NotImplementedError("the task queue is not implemented yet")

    def pending(self) -> list[Task]:
        raise NotImplementedError("the task queue is not implemented yet")
