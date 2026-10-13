"""Shorter reference solution for 02-load-balancer."""

import heapq
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


# functional Enum API: each member's value equals its name
WorkerState = Enum("WorkerState", {m: m for m in "IDLE BUSY DRAINING FAILED REMOVED".split()})
TaskState = Enum("TaskState", {m: m for m in "PENDING ASSIGNED COMPLETED EXPIRED DEAD".split()})


class InvalidTransition(Exception):
    pass


W, T = WorkerState, TaskState
ALLOWED_TRANSITIONS = {
    W.IDLE: {W.BUSY, W.DRAINING, W.FAILED},
    W.BUSY: {W.IDLE, W.DRAINING, W.FAILED},
    W.DRAINING: {W.REMOVED, W.FAILED},
    W.FAILED: {W.IDLE, W.REMOVED},
    W.REMOVED: set(),
}


@dataclass
class Worker:
    id: str
    capacity: int
    last_seen: float
    state: WorkerState = W.IDLE
    in_flight: int = 0


@dataclass
class Task:
    id: str
    priority: int
    deadline: Optional[float]
    seq: int  # submission order, never changes
    state: TaskState = T.PENDING
    attempt: int = 1
    worker: Optional[str] = None
    assigned_at: float = 0.0

    def overdue(self, now: float) -> bool:
        return self.deadline is not None and now > self.deadline


class LoadBalancer:
    def __init__(self, now: Callable[[], float], *, heartbeat_timeout=10.0,
                 task_timeout=30.0, max_retries=3, scale_cooldown=30.0):
        self._now = now
        self.heartbeat_timeout = heartbeat_timeout
        self.task_timeout = task_timeout
        self.max_retries = max_retries
        self.scale_cooldown = scale_cooldown
        self._workers: dict[str, Worker] = {}  # insertion = registration order
        self._tasks: dict[str, Task] = {}
        self._assigned: dict[str, Task] = {}   # insertion = assignment order
        self._heap: list[tuple[int, int, str]] = []
        self._dead: list[str] = []
        self._last_scale = float("-inf")  # time of last nonzero decision

    def _transition(self, w: Worker, new: WorkerState) -> None:
        if new not in ALLOWED_TRANSITIONS[w.state]:
            raise InvalidTransition(f"{w.id}: {w.state.value} -> {new.value}")
        w.state = new

    def _sync(self, w: Worker) -> None:
        """Bookkeeping after in_flight changes; skips same-state moves."""
        if w.state in (W.IDLE, W.BUSY):
            target = W.BUSY if w.in_flight else W.IDLE
            if target is not w.state:
                self._transition(w, target)
        elif w.state is W.DRAINING and w.in_flight == 0:
            self._transition(w, W.REMOVED)

    def register_worker(self, worker_id: str, capacity: int = 1) -> None:
        if worker_id in self._workers or capacity < 1:
            raise ValueError(f"bad worker {worker_id!r} / capacity {capacity}")
        self._workers[worker_id] = Worker(worker_id, capacity, self._now())

    def worker_state(self, worker_id: str) -> WorkerState:
        return self._workers[worker_id].state

    def heartbeat(self, worker_id: str) -> None:
        w = self._workers[worker_id]
        if w.state is W.REMOVED:
            raise InvalidTransition(f"{worker_id} is REMOVED")
        w.last_seen = self._now()
        if w.state is W.FAILED:
            self._transition(w, W.IDLE)

    def drain_worker(self, worker_id: str) -> None:
        w = self._workers[worker_id]
        if w.state is W.FAILED:
            self._transition(w, W.REMOVED)
        else:
            self._transition(w, W.DRAINING)
            self._sync(w)  # removes it right away if nothing is in flight

    def submit(self, task_id: str, priority: int, deadline: Optional[float] = None) -> bool:
        if task_id in self._tasks:
            return False
        t = Task(task_id, priority, deadline, seq=len(self._tasks))
        self._tasks[task_id] = t
        heapq.heappush(self._heap, (-priority, t.seq, task_id))
        return True

    def task_state(self, task_id: str) -> TaskState:
        return self._tasks[task_id].state

    def dead_letter(self) -> list[str]:
        return list(self._dead)

    def _pick_worker(self) -> Optional[Worker]:
        eligible = [w for w in self._workers.values()
                    if w.state in (W.IDLE, W.BUSY) and w.in_flight < w.capacity]
        return min(eligible, key=lambda w: w.in_flight, default=None)  # ties -> first registered

    def _next_pending(self, now: float) -> Optional[Task]:
        while self._heap:
            t = self._tasks[heapq.heappop(self._heap)[2]]
            if t.state is T.PENDING and t.overdue(now):
                t.state = T.EXPIRED
            elif t.state is T.PENDING:
                return t
            # anything else is a stale heap entry (lazy deletion): skip it
        return None

    def dispatch(self) -> list[tuple[str, str, int]]:
        now = self._now()
        out = []
        # pick the worker first: if none is free, no task gets popped (or expired)
        while (w := self._pick_worker()) and (t := self._next_pending(now)):
            t.state, t.worker, t.assigned_at = T.ASSIGNED, w.id, now
            self._assigned[t.id] = t
            w.in_flight += 1
            self._sync(w)
            out.append((t.id, w.id, t.attempt))
        return out

    def complete(self, worker_id: str, task_id: str, attempt: int) -> bool:
        return self._end_attempt(worker_id, task_id, attempt, failed=False)

    def fail(self, worker_id: str, task_id: str, attempt: int) -> bool:
        return self._end_attempt(worker_id, task_id, attempt, failed=True)

    def _end_attempt(self, worker_id: str, task_id: str, attempt: int, failed: bool) -> bool:
        t = self._assigned.get(task_id)
        if t is None or t.worker != worker_id or t.attempt != attempt:
            return False  # unknown / not ASSIGNED / stale lease: change nothing
        del self._assigned[t.id]
        w = self._workers[worker_id]
        w.in_flight -= 1
        if not failed:
            t.state = T.COMPLETED
        elif t.attempt > self.max_retries:
            t.state = T.DEAD
            self._dead.append(t.id)
        else:
            t.attempt += 1
            t.state = T.PENDING
            heapq.heappush(self._heap, (-t.priority, t.seq, t.id))
        self._sync(w)
        return True

    def tick(self) -> None:
        now = self._now()
        # 1. heartbeat timeouts; FAILED first so _sync leaves the worker alone
        for w in self._workers.values():
            if w.state in (W.IDLE, W.BUSY, W.DRAINING) and now - w.last_seen > self.heartbeat_timeout:
                self._transition(w, W.FAILED)
                for t in [t for t in self._assigned.values() if t.worker == w.id]:
                    self.fail(w.id, t.id, t.attempt)
        # 2. task timeouts, in assignment order (copy: fail() mutates the dict)
        for t in list(self._assigned.values()):
            if now - t.assigned_at > self.task_timeout:
                self.fail(t.worker, t.id, t.attempt)
        # 3. pending deadlines (includes tasks requeued above)
        for t in self._tasks.values():
            if t.state is T.PENDING and t.overdue(now):
                t.state = T.EXPIRED

    def scaling_decision(self) -> int:
        now = self._now()
        if now - self._last_scale < self.scale_cooldown:
            return 0
        pending = sum(t.state is T.PENDING for t in self._tasks.values())
        eligible = [w for w in self._workers.values() if w.state in (W.IDLE, W.BUSY)]
        cap = sum(w.capacity for w in eligible)
        busy = sum(w.in_flight for w in eligible)
        if pending > 2 * cap:
            decision = 1
        elif len(eligible) > 1 and busy / cap < 0.25:
            decision = -1
        else:
            return 0  # returning 0 never starts a cooldown
        self._last_scale = now
        return decision
