from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Decision(Enum):
    AUTO_ACCEPT = "auto_accept"
    HUMAN_REVIEW = "human_review"


@dataclass
class Prediction:
    item_id: str
    task: str
    label: str
    confidence: float | None
    sensitive: bool
    priority: int
    created_at: datetime


@dataclass
class Reviewer:
    reviewer_id: str
    skills: set
    active: bool
    capacity: int


@dataclass
class Routed:
    prediction: Prediction
    decision: Decision
    reason: str
    reviewer: str | None = None


@dataclass
class TaskPolicy:
    threshold: float
    priority: int
    always_review: set = field(default_factory=set)
