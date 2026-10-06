from dataclasses import dataclass


@dataclass
class Task:
    task_id: str
    priority: int
    enqueued_ms: int
    max_attempts: int
    status: str = "pending"
    attempts: int = 0
    first_leased_ms: int | None = None


@dataclass
class Lease:
    task_id: str
    worker_id: str
    deadline_ms: int


@dataclass(frozen=True)
class Event:
    ts_ms: int
    worker_id: str
    action: str
    task_id: str | None


class Worker:
    """A worker seen in the event log, with the tasks it finished in order."""

    completed = []

    def __init__(self, worker_id):
        self.worker_id = worker_id

    def record(self, task_id):
        self.completed.append(task_id)
