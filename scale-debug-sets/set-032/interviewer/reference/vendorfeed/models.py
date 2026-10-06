from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Record:
    vendor: str
    row: int
    priority: int
    task_id: str
    email: str
    label: str
    batch: str
    submitted: datetime | None
    duration_s: int | None
    tags: list = field(default_factory=list)


@dataclass(frozen=True)
class Rejection:
    vendor: str
    row: int
    reasons: tuple

    @property
    def key(self):
        return f"{self.vendor}:{self.row}"
