from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Tier(Enum):
    EXPERT = "expert"
    STANDARD = "standard"
    TRAINEE = "trainee"


@dataclass(frozen=True)
class Annotator:
    id: str
    tier: Tier
    active: bool
    queues: frozenset  # empty means every queue


@dataclass(frozen=True)
class Item:
    id: str
    queue: str
    min_votes: int
    closes_at: datetime | None


@dataclass(frozen=True)
class Queue:
    name: str
    labels: tuple
    threshold: float
    min_votes: int


@dataclass(frozen=True)
class Vote:
    vote_id: str
    vendor: str
    item_id: str
    annotator_id: str
    label: str
    submitted_at: datetime


@dataclass
class Result:
    item_id: str
    status: str
    label: str | None
    agreement: float | None
    votes: int
    expert_dissent: bool = False
