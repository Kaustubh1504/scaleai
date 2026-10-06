from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Prediction:
    item_id: str
    model_version: str
    label: str
    confidence: float | None
    priority: int
    language: str
    received_at: datetime


@dataclass
class Reviewer:
    id: str
    languages: frozenset
    capacity: int
    active: bool
    assigned: list = field(default_factory=list)

    @property
    def remaining(self):
        return self.capacity - len(self.assigned)


@dataclass(frozen=True)
class Decision:
    item_id: str
    decision: str
    reason: str
    threshold: float


@dataclass(frozen=True)
class Review:
    review_id: str
    item_id: str
    reviewer_id: str
    model_label: str
    human_label: str
    finished_at: datetime
