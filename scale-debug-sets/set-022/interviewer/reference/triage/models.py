from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Route(Enum):
    AUTO = "auto"
    HUMAN = "human"


@dataclass
class Prediction:
    pred_id: str
    task_type: str
    lang: str
    confidence: float | None
    flags: list
    priority: int
    created_at: datetime


@dataclass
class Reviewer:
    id: str
    languages: list
    capacity: int
    active: bool


@dataclass
class Decision:
    prediction: Prediction
    route: Route
    reason: str
    threshold: float


@dataclass
class Thresholds:
    default: float
    by_type: dict = field(default_factory=dict)
    always_human: set = field(default_factory=set)

    def for_task(self, task_type):
        return self.by_type.get(task_type, self.default)
