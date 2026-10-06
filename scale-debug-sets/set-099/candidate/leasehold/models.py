from dataclasses import dataclass
from datetime import datetime


class LeaseError(Exception):
    """An event that the broker refuses to apply."""


class UnknownTask(LeaseError):
    pass


class UnknownWorker(LeaseError):
    pass


class TaskClosed(LeaseError):
    """The task is already done or dead."""


@dataclass
class Task:
    id: str
    type: str
    priority: int  # 1 is the most urgent
    created_at: datetime
    max_attempts: int
    status: str = "pending"
    attempts: int = 0
    first_claimed_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass
class Lease:
    task_id: str
    worker: str
    expires_at: datetime


@dataclass(frozen=True)
class Event:
    at: datetime
    worker: str
    action: str
    task_id: str | None
