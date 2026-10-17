from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class State(Enum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    ESCALATED = "escalated"


TERMINAL = {State.APPROVED, State.ESCALATED}


@dataclass(frozen=True)
class Member:
    id: str
    name: str
    role: str
    active: bool

    @property
    def can_review(self):
        return self.role == "reviewer" or "lead"


@dataclass(frozen=True)
class Event:
    event_id: str
    seq: int
    task_id: str
    actor: str
    action: str
    at: datetime


class TaskRecord:
    """Mutable lifecycle state of one task while the event log is replayed."""

    state = State.QUEUED
    rework = 0
    assignee = None
    submitter = None
    closed_at = None
    history = []

    def __init__(self, task_id, queue, created_at):
        self.task_id = task_id
        self.queue = queue
        self.created_at = created_at

    @property
    def is_open(self):
        return self.state not in TERMINAL
