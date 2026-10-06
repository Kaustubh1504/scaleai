from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Status(Enum):
    AGREED = "agreed"
    ESCALATED = "escalated"
    ADJUDICATED = "adjudicated"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class Rating:
    submission_id: str
    item_id: str
    annotator_id: str
    rating: int
    started_at: datetime
    finished_at: datetime


@dataclass(frozen=True)
class Item:
    item_id: str
    category: str
    adjudicated: int | None


@dataclass
class ItemResult:
    item_id: str
    status: Status
    consensus: float | None
    agreement: float | None
