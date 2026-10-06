from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Annotation:
    task_id: str
    annotator_id: str
    label: str
    submitted_at: datetime


@dataclass
class Annotator:
    id: str
    name: str
    active: bool


@dataclass
class QualityRow:
    accuracy: float
    gold_answered: int
    blocked: bool = False


@dataclass
class Consensus:
    task_id: str
    status: str
    label: str | None
    confidence: float | None
    votes: int
