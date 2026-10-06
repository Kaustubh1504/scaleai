from dataclasses import dataclass
from datetime import datetime

PENDING = "pending"
LEASED = "leased"
DONE = "done"
DEAD = "dead"


@dataclass
class Task:
    id: str
    priority: int
    created_at: datetime
    max_attempts: int = 3
    attempts: int = 0
    status: str = PENDING

    def exhausted(self):
        return self.attempts >= self.max_attempts


@dataclass
class Lease:
    task_id: str
    worker_id: str
    leased_at: datetime


@dataclass
class Event:
    ts: datetime
    worker_id: str
    action: str
    task_id: str | None
