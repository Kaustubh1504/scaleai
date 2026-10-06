from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class State(Enum):
    QUEUED = "queued"
    LABELING = "labeling"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    ESCALATED = "escalated"
    APPROVED = "approved"


@dataclass(frozen=True)
class Person:
    person_id: str
    role: str
    active: bool


@dataclass
class Task:
    task_id: str
    project: str
    priority: int
    created: datetime
    state: State
    claim_holder: str | None = None
    claim_at: datetime | None = None
    rework: int = 0
    approved_at: datetime | None = None


@dataclass(frozen=True)
class Event:
    line: int
    ts: datetime
    task_id: str
    actor: str
    action: str


@dataclass(frozen=True)
class Transition:
    """An event that was applied, plus when the actor's review claim started (if any)."""
    ts: datetime
    task_id: str
    actor: str
    action: str
    claim_at: datetime | None = None
