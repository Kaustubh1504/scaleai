from dataclasses import dataclass
from datetime import datetime

PENDING = "pending"
LEASED = "leased"
DONE = "done"
DEAD = "dead"


@dataclass
class Task:
    id: str
    queue: str
    priority: int
    created_at: datetime
    max_attempts: int
    status: str = PENDING
    attempts: int = 0
    extensions: int = 0


@dataclass
class Lease:
    task: Task
    worker: str
    leased_at: datetime
    expires_at: datetime
    extensions: int = 0


@dataclass
class Event:
    at: datetime
    worker: str
    action: str
    queue: str
    task_id: str
