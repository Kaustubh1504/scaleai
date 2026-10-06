from dataclasses import dataclass
from datetime import datetime

SKIP = "skip"


@dataclass(frozen=True)
class Project:
    id: str
    min_votes: int
    agreement: float


@dataclass(frozen=True)
class Annotation:
    task_id: str
    project: str
    annotator_id: str
    label: str
    submitted_at: datetime

    @property
    def skipped(self):
        return self.label == SKIP


@dataclass
class TaskResult:
    task_id: str
    project: str
    status: str
    label: str | None
    votes: int


@dataclass
class AgreementRow:
    agreed_tasks: int
    rate: float | None
    skips: int
