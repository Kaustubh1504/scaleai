from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Item:
    id: str
    rubric: str
    gold: int | None


@dataclass(frozen=True)
class Rating:
    item_id: str
    annotator_id: str
    score: int
    submitted_at: datetime


@dataclass
class Result:
    item_id: str
    rubric: str
    status: str
    score: float | None
    agreement: float | None
    votes: int
