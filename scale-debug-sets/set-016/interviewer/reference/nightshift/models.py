from dataclasses import dataclass, field
from datetime import datetime

PENDING = "pending"
SUCCEEDED = "succeeded"
DEAD = "dead"
SKIPPED = "skipped"


@dataclass
class Job:
    job_id: str
    name: str
    priority: int
    depends_on: list[str]
    max_retries: int
    submitted_at: datetime
    duration_s: int
    status: str = PENDING
    attempts: int = 0
    finished_round: int | None = None
    history: list[str] = field(default_factory=list)

    @property
    def retries_left(self):
        return self.max_retries - (self.attempts - 1)

    def can_retry(self):
        return self.retries_left > 0
