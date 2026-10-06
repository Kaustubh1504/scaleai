from dataclasses import dataclass
from datetime import datetime

from .enums import Route


@dataclass
class Prediction:
    item_id: str
    model: str
    label: str
    confidence: float | None
    received_at: datetime
    lang: str
    flagged: bool


@dataclass
class LabelRule:
    label: str
    severity: int
    threshold: float | None
    sensitive: bool


@dataclass
class Decision:
    item_id: str
    route: Route
    reason: str
    severity: int


@dataclass
class Reviewer:
    reviewer_id: str
    pool: str
    active: bool
    capacity: int
    senior: bool
    load: int = 0


@dataclass
class Review:
    item_id: str
    model: str
    model_label: str
    confidence: float
    human_label: str
