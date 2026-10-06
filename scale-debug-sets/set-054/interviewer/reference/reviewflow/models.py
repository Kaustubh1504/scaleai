from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class State(Enum):
    SUBMITTED = "submitted"
    L1_REVIEW = "l1_review"
    AWAITING_L2 = "awaiting_l2"
    L2_REVIEW = "l2_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    REJECTED = "rejected"


WAITING = {State.SUBMITTED, State.AWAITING_L2}
DECIDED = {State.APPROVED, State.REJECTED}


class ReviewError(Exception):
    """Base class for events the review machine refuses."""


class UnknownTask(ReviewError):
    pass


class InvalidTransition(ReviewError):
    pass


class AssignmentError(ReviewError):
    """The actor isn't allowed to act on this task right now."""


class ConflictOfInterest(AssignmentError):
    """The actor wrote the task, or already reviewed it at level 1."""


class Task:
    state = State.SUBMITTED
    revision = 1
    l1_reviewer = None
    l2_reviewer = None
    decided_at = None

    def __init__(self, task_id, author, priority, submitted_at):
        self.task_id = task_id
        self.author = author
        self.priority = priority
        self.submitted_at = submitted_at
        self.entered_at = submitted_at
        self.history = []
        self.history.append(State.SUBMITTED)

    def move(self, state, at):
        self.state = state
        self.entered_at = at
        self.history.append(state)
        if state in DECIDED:
            self.decided_at = at


@dataclass
class Event:
    at: datetime
    task_id: str
    actor: str
    action: str
