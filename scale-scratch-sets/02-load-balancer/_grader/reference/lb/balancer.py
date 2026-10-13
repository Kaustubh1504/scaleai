"""Reference solution for 02-load-balancer. Graders only; the candidate never sees this."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class WorkerState(Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    DRAINING = "DRAINING"
    FAILED = "FAILED"
    REMOVED = "REMOVED"


class TaskState(Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    DEAD = "DEAD"


class InvalidTransition(Exception):
    pass


W = WorkerState
ALLOWED_TRANSITIONS: dict[WorkerState, set[WorkerState]] = {
    W.IDLE: {W.BUSY, W.DRAINING, W.FAILED},
    W.BUSY: {W.IDLE, W.DRAINING, W.FAILED},
    W.DRAINING: {W.REMOVED, W.FAILED},
    W.FAILED: {W.IDLE, W.REMOVED},
    W.REMOVED: set(),
}


@dataclass
class _Worker:
    id: str
    capacity: int
    order: int
    last_seen: float
    state: WorkerState = WorkerState.IDLE
    tasks: dict = field(default_factory=dict)  # task_id -> assign seq (insertion = assignment order)


@dataclass
class _Task:
    id: str
    priority: int
    deadline: Optional[float]
    seq: int
    state: TaskState = TaskState.PENDING
    attempt: int = 1  # attempt number of the next (or current) assignment
    worker: Optional[str] = None
    assigned_at: float = 0.0
    assign_seq: int = 0


class LoadBalancer:
    def __init__(self, now: Callable[[], float], *, heartbeat_timeout: float = 10.0,
                 task_timeout: float = 30.0, max_retries: int = 3, scale_cooldown: float = 30.0):
        self._now = now
        self.heartbeat_timeout = heartbeat_timeout
        self.task_timeout = task_timeout
        self.max_retries = max_retries
        self.scale_cooldown = scale_cooldown
        self._workers: dict[str, _Worker] = {}
        self._tasks: dict[str, _Task] = {}
        self._heap: list[tuple[int, int, str]] = []
        self._seq = 0
        self._assign_seq = 0
        self._dead: list[str] = []
        self._last_scale: Optional[float] = None

    # ---- state machine -------------------------------------------------
    def _transition(self, w: _Worker, new: WorkerState) -> None:
        if new not in ALLOWED_TRANSITIONS[w.state]:
            raise InvalidTransition(f"{w.id}: {w.state.value} -> {new.value}")
        w.state = new

    def _sync(self, w: _Worker) -> None:
        """Automatic bookkeeping after in_flight changes."""
        if w.state in (W.IDLE, W.BUSY):
            target = W.BUSY if w.tasks else W.IDLE
            if target is not w.state:
                self._transition(w, target)
        elif w.state is W.DRAINING and not w.tasks:
            self._transition(w, W.REMOVED)

    # ---- workers -------------------------------------------------------
    def register_worker(self, worker_id: str, capacity: int = 1) -> None:
        if worker_id in self._workers:
            raise ValueError(f"duplicate worker {worker_id}")
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self._workers[worker_id] = _Worker(worker_id, capacity, len(self._workers), self._now())

    def heartbeat(self, worker_id: str) -> None:
        w = self._workers[worker_id]
        if w.state is W.REMOVED:
            raise InvalidTransition(f"{worker_id} is REMOVED")
        w.last_seen = self._now()
        if w.state is W.FAILED:
            self._transition(w, W.IDLE)

    def worker_state(self, worker_id: str) -> WorkerState:
        return self._workers[worker_id].state

    def drain_worker(self, worker_id: str) -> None:
        w = self._workers[worker_id]
        if w.state is W.FAILED:
            self._transition(w, W.REMOVED)
            return
        self._transition(w, W.DRAINING)
        self._sync(w)

    # ---- tasks ---------------------------------------------------------
    def submit(self, task_id: str, priority: int, deadline: Optional[float] = None) -> bool:
        if task_id in self._tasks:
            return False
        t = _Task(task_id, priority, deadline, self._seq)
        self._seq += 1
        self._tasks[task_id] = t
        heapq.heappush(self._heap, (-priority, t.seq, task_id))
        return True

    def task_state(self, task_id: str) -> TaskState:
        return self._tasks[task_id].state

    def dead_letter(self) -> list[str]:
        return list(self._dead)

    def _pick_worker(self) -> Optional[_Worker]:
        best = None
        for w in self._workers.values():  # registration order
            if w.state in (W.IDLE, W.BUSY) and len(w.tasks) < w.capacity:
                if best is None or len(w.tasks) < len(best.tasks):
                    best = w
        return best

    def dispatch(self) -> list[tuple[str, str, int]]:
        out = []
        now = self._now()
        while True:
            w = self._pick_worker()
            if w is None:
                break
            t = None
            while self._heap:
                _, _, tid = heapq.heappop(self._heap)
                cand = self._tasks[tid]
                if cand.state is not TaskState.PENDING:
                    continue  # stale heap entry
                if cand.deadline is not None and now > cand.deadline:
                    cand.state = TaskState.EXPIRED
                    continue
                t = cand
                break
            if t is None:
                break
            t.state = TaskState.ASSIGNED
            t.worker = w.id
            t.assigned_at = now
            t.assign_seq = self._assign_seq
            self._assign_seq += 1
            w.tasks[t.id] = t.assign_seq
            self._sync(w)
            out.append((t.id, w.id, t.attempt))
        return out

    def _lease(self, worker_id: str, task_id: str, attempt: int) -> Optional[_Task]:
        t = self._tasks.get(task_id)
        if t is None or t.state is not TaskState.ASSIGNED or t.worker != worker_id or t.attempt != attempt:
            return None
        return t

    def _release(self, t: _Task) -> _Worker:
        w = self._workers[t.worker]
        del w.tasks[t.id]
        t.worker = None
        return w

    def _attempt_failed(self, t: _Task) -> None:
        """t has already been released from its worker."""
        if t.attempt > self.max_retries:
            t.state = TaskState.DEAD
            self._dead.append(t.id)
        else:
            t.attempt += 1
            t.state = TaskState.PENDING
            heapq.heappush(self._heap, (-t.priority, t.seq, t.id))

    def complete(self, worker_id: str, task_id: str, attempt: int) -> bool:
        t = self._lease(worker_id, task_id, attempt)
        if t is None:
            return False
        w = self._release(t)
        t.state = TaskState.COMPLETED
        self._sync(w)
        return True

    def fail(self, worker_id: str, task_id: str, attempt: int) -> bool:
        t = self._lease(worker_id, task_id, attempt)
        if t is None:
            return False
        w = self._release(t)
        self._attempt_failed(t)
        self._sync(w)
        return True

    # ---- time ----------------------------------------------------------
    def tick(self) -> None:
        now = self._now()
        # 1. heartbeat timeouts
        for w in self._workers.values():
            if w.state in (W.IDLE, W.BUSY, W.DRAINING) and now - w.last_seen > self.heartbeat_timeout:
                self._transition(w, W.FAILED)
                for tid in list(w.tasks):
                    t = self._tasks[tid]
                    self._release(t)
                    self._attempt_failed(t)
        # 2. task timeouts, in assignment order
        timed_out = sorted(
            (t for t in self._tasks.values()
             if t.state is TaskState.ASSIGNED and now - t.assigned_at > self.task_timeout),
            key=lambda t: t.assign_seq)
        for t in timed_out:
            w = self._release(t)
            self._attempt_failed(t)
            self._sync(w)
        # 3. pending deadlines
        for t in self._tasks.values():
            if t.state is TaskState.PENDING and t.deadline is not None and now > t.deadline:
                t.state = TaskState.EXPIRED

    # ---- scaling -------------------------------------------------------
    def scaling_decision(self) -> int:
        now = self._now()
        if self._last_scale is not None and now - self._last_scale < self.scale_cooldown:
            return 0
        pending = sum(1 for t in self._tasks.values() if t.state is TaskState.PENDING)
        eligible = [w for w in self._workers.values() if w.state in (W.IDLE, W.BUSY)]
        cap = sum(w.capacity for w in eligible)
        busy = sum(len(w.tasks) for w in eligible)
        decision = 0
        if pending > 2 * cap:
            decision = 1
        elif len(eligible) > 1 and busy / cap < 0.25:
            decision = -1
        if decision:
            self._last_scale = now
        return decision
