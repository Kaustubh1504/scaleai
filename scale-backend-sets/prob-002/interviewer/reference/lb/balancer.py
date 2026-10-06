"""Routes tasks to workers.

Workers are tried in round-robin order (registration order, continuing after
the most recently tried worker), skipping any that are not ACTIVE. Worker
errors drive state changes and failover; heartbeats and ``check_health()``
drive liveness; ``submit()`` / ``drain()`` add a priority queue on top.

Keep the constructor and the public method signatures: other services (and
the interviewer's tests) call them.

Not thread-safe: one thread owns a balancer and calls all of its methods.
"""

from __future__ import annotations

import heapq
import itertools
import logging

from lb.health import WorkerHealth, parse_heartbeat
from lb.models import DispatchResult, Task, Worker, WorkerState
from lb.registry import WorkerRegistry
from mock_services.clock import Clock, RealClock
from mock_services.workers import TaskFailedError, WorkerOverloadedError, WorkerTimeoutError, WorkerUnreachableError

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
        self._health: dict[str, WorkerHealth] = {}
        self._seq = itertools.count()
        self._last_tried_seq = -1  # registration seq of the most recently tried worker
        self._queue: list[tuple[int, int, Task]] = []  # heap of (-priority, submit order, task)
        self._queued_ids: set[str] = set()

    # ------------------------------------------------------------ membership

    def add_worker(self, worker: Worker) -> None:
        self.registry.register(worker)  # ValueError on a duplicate id
        self._health[worker.worker_id] = WorkerHealth(seq=next(self._seq), last_seen=self.clock.time())
        log.info("worker %s joined", worker.worker_id)

    def remove_worker(self, worker_id: str) -> None:
        self.registry.unregister(worker_id)  # KeyError if unknown
        del self._health[worker_id]
        log.info("worker %s left", worker_id)

    def worker_state(self, worker_id: str) -> WorkerState:
        try:
            health = self._health[worker_id]
        except KeyError:
            raise KeyError(f"unknown worker {worker_id!r}") from None
        return health.current(self.clock.time())

    # --------------------------------------------------------------- routing

    def dispatch(self, task: Task) -> DispatchResult:
        """Send ``task`` to the next ACTIVE worker, failing over until one succeeds."""
        return self._dispatch(task, limit=None)

    def _rotation(self) -> list[Worker]:
        # Registry order is registration order, so seq increases along it.
        workers = list(self.registry)
        start = next((i for i, w in enumerate(workers) if self._health[w.worker_id].seq > self._last_tried_seq), 0)
        return workers[start:] + workers[:start]

    def _dispatch(self, task: Task, limit: int | None) -> DispatchResult:
        """Try each ACTIVE worker at most once, and at most ``limit`` workers if given."""
        for worker in self._rotation():
            if limit is not None and limit <= 0:
                break
            health = self._health[worker.worker_id]
            if health.current(self.clock.time()) is not WorkerState.ACTIVE:
                continue
            task.attempts += 1
            limit = None if limit is None else limit - 1
            self._last_tried_seq = health.seq
            try:
                result = worker.process(task.payload, timeout=self.task_timeout_s)
            except WorkerOverloadedError:
                health.mark_overloaded(self.clock.time(), self.overload_cooldown_s)
                log.warning("worker %s overloaded; task %s fails over", worker.worker_id, task.id)
            except (WorkerUnreachableError, WorkerTimeoutError) as exc:
                health.mark_unreachable()
                log.warning("worker %s unreachable (%s); task %s fails over", worker.worker_id, exc, task.id)
            except TaskFailedError as exc:
                raise TaskFailed(task.id, worker.worker_id, str(exc)) from exc
            else:
                log.debug("task %s handled by %s", task.id, worker.worker_id)
                return DispatchResult(task.id, worker.worker_id, result, task.attempts)
        raise NoWorkersAvailable(task.id)

    # ---------------------------------------------------------------- health

    def on_heartbeat(self, payload: dict) -> None:
        parsed = parse_heartbeat(payload)
        if parsed is None:
            log.warning("ignoring malformed heartbeat %r", payload)
            return
        worker_id, in_flight, capacity = parsed
        health = self._health.get(worker_id)
        if health is None:
            log.info("ignoring heartbeat from unknown worker %s", worker_id)
            return
        before = health.state
        # Liveness is judged on our clock; the payload's ts comes from the worker's clock.
        health.record_heartbeat(self.clock.time(), in_flight, capacity, self.overload_cooldown_s)
        if health.state is not before:
            log.info("worker %s: %s -> %s", worker_id, before.value, health.state.value)

    def check_health(self) -> None:
        """Mark workers that have not sent a heartbeat for too long as UNREACHABLE."""
        now = self.clock.time()
        for worker_id, health in self._health.items():
            if health.state is not WorkerState.UNREACHABLE and health.is_stale(now, self.heartbeat_timeout_s):
                health.mark_unreachable()
                log.warning("worker %s missed heartbeats; marked unreachable", worker_id)

    # ----------------------------------------------------------------- queue

    def submit(self, task: Task) -> None:
        if task.id in self._queued_ids:
            raise ValueError(f"task {task.id!r} is already pending")
        heapq.heappush(self._queue, (-task.priority, next(self._seq), task))
        self._queued_ids.add(task.id)

    def pending(self) -> list[Task]:
        return [task for _, _, task in sorted(self._queue)]

    def drain(self) -> list[DispatchResult]:
        """Dispatch queued tasks, highest priority first, until the queue is empty or no worker can take one."""
        results = []
        while self._queue:
            task = self._queue[0][2]  # peek: the task stays queued unless it is resolved
            try:
                results.append(self._dispatch(task, limit=self.max_attempts - task.attempts))
            except TaskFailed as exc:
                self._give_up(task, exc.reason)
                continue
            except NoWorkersAvailable:
                if task.attempts < self.max_attempts:
                    break  # leave it at the front; a later drain retries it
                self._give_up(task, f"no worker completed it in {task.attempts} attempts")
                continue
            self._pop(task)
        return results

    def _pop(self, task: Task) -> None:
        heapq.heappop(self._queue)
        self._queued_ids.discard(task.id)

    def _give_up(self, task: Task, reason: str) -> None:
        self._pop(task)
        self.failed.append((task, reason))
        log.warning("task %s failed: %s", task.id, reason)
