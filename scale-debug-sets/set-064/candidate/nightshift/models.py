from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Job:
    job_id: str
    queue: str
    priority: int
    submitted_at: datetime
    duration_min: int
    max_retries: int
    deadline: datetime | None
    depends_on: list[str] = field(default_factory=list)
    # filled in by the dispatcher
    status: str = "pending"
    attempts: int = 0
    ready_at: datetime | None = None
    first_start: datetime | None = None
    finished_at: datetime | None = None


class QueueLog:
    """Every attempt dispatched on one queue, in dispatch order."""

    def __init__(self, name, entries=[]):
        self.name = name
        self.entries = entries

    def record(self, job_id: str, attempt: int, outcome: str) -> None:
        self.entries.append((job_id, attempt, outcome))
