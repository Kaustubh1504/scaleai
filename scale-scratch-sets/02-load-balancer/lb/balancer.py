import heapq
from dataclasses import dataclass
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

W, T = WorkerState, TaskState

ALLOWED_TRANSITIONS = {
    W.IDLE: {W.BUSY, W.DRAINING, W.FAILED},
    W.BUSY: {W.IDLE, W.DRAINING, W.FAILED},
    W.DRAINING: {W.REMOVED, W.FAILED},
    W.FAILED: {W.IDLE, W.REMOVED},
    W.REMOVED: set()
}

@dataclass
class Worker:
    id: str
    capacity: int
    last_seen: float
    stat: WorkerState = W.IDLE
    in_flight: int = 0

@dataclass
class Task:
    id: str
    priority: int
    deadline: Optional[float]
    seq: int
    state: TaskState = T.PENDING
    attempt: int = 1
    worker: Optional[str]= None
    assigned_at: float = 0.0

    def overdue(self, now: float) -> bool:
        return self.deadline is not None and now>self.deadline
    

class LoadBalance:
    def __init__(self, now, heartbeat_timeout=10.0, task_timeout=30.0,
                 max_retries=3,scale_cooldown=30.0):
        self.now = now
        self.heartbeat_timeout = heartbeat_timeout
        self.task_timeout = task_timeout
        self.max_retries = max_retries
        self.scale_cooldown = scale_cooldown
        self.workers = {}
        self.tasks = {}
        self.assigned = {}
        self.heap = []
        self.dead = []
        self.last_scale = float("-inf")
    
    def transition(self, w:Worker, new: WorkerState):
        if new not in ALLOWED_TRANSITIONS:
            raise InvalidTransition(f"invalid transiton")
        w.state = new
    
    def sync(self, w):
        if w.state in (W.IDLE, W.BUSY):
            target = W.Busy if w.in_flight else W.IDLE
            if target is not w.state:
                self.transition(w, target)
                
    def register_worker(self, worker_id, capacity=1):
        if worker_id in self.workers or capacity<1:
            raise ValueError(f"bad worker")
        self.workers[worker_id] = Worker(worker_id, capacity, self.now())
    
    def worker_state(self, worker_id):
        return self.workers[worker_id].state
    
    def submit(self, task_id, priority, deadline):
        if task_id in self.tasks:
            return False
        t = Task(task_id,priority, deadline, seq=len(self.tasks))
        self.tasks[task_id] = t
        heapq.heappush(self.heap, (-priority, t.seq, task_id))
        return True
    
    def task_state(self, task_id):
        return self.tasks[task_id].state
    
    def pick_worker(self):
        eligible = [w for w in self.workers.values() if w.state in (W.IDLE, W.BUSY) and w.in_flight < w.capacity]
        return min(eligible, key=lambda w: w.in_flight, default=None)
    
    def next_pending(self, now):
        while self.heap:
            t = self.tasks[heapq.heappop(self.heap)[2]]
            if t.state is T.PENDING and t.overdue(now):
                t.state = T.EXPIRED
            elif t.state is T.PENDING:
                return t
            
        return None
    
    def dispatch(self) -> list[tuple[str, str, int]]:
        now = self.now()
        out = []
        # pick the worker first: if none is free, no task gets popped (or expired)
        while (w := self.pick_worker()) and (t := self.next_pending(now)):
            t.state, t.worker, t.assigned_at = T.ASSIGNED, w.id, now
            self.assigned[t.id] = t
            w.in_flight += 1
            self.sync(w)
            out.append((t.id, w.id, t.attempt))
        return out
    
    def complete(self, worker_id: str, task_id: str, attempt: int) -> bool:
        return self.end_attempt(worker_id, task_id, attempt, failed=False)
    
    def fail(self, worker_id: str, task_id: str, attempt: int) -> bool:
        return self.end_attempt(worker_id, task_id, attempt, failed=True)

    def dead_letter(self) -> list[str]:
        return list(self.dead)

    def end_attempt(self, worker_id: str, task_id: str, attempt: int, failed: bool) -> bool:
        t = self.assigned.get(task_id)
        if t is None or t.worker != worker_id or t.attempt != attempt:
            return False  # unknown / not ASSIGNED / stale lease: change nothing
        del self.assigned[t.id]
        w = self.workers[worker_id]
        w.in_flight -= 1
        if not failed:
            t.state = T.COMPLETED
        elif t.attempt > self.max_retries:
            t.state = T.DEAD
            self.dead.append(t.id)
        else:
            t.attempt += 1
            t.state = T.PENDING
            heapq.heappush(self.heap, (-t.priority, t.seq, t.id))
        self.sync(w)
        return True

def main():
    print(WorkerState.IDLE, WorkerState.IDLE.value)
    print([m.name for m in TaskState])
    
if __name__ == "__main__":
    main()