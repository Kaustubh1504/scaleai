from dataclasses import dataclass, field


class LeaseError(Exception):
    """The event refers to a task the worker cannot act on."""


class LeaseExpired(LeaseError):
    """The worker held this task, but its lease ran out."""


class NotOwner(LeaseError):
    """The task is not leased to this worker and never was."""


@dataclass
class Task:
    id: str
    priority: int
    enqueued_ms: int
    max_attempts: int
    state: str = "ready"
    owner: str | None = None
    expires_ms: int | None = None
    attempts: int = 0
    first_claim_ms: int | None = None
    completed_by: str | None = None
    past_owners: list = field(default_factory=list)


@dataclass(frozen=True)
class Event:
    at_ms: int
    worker_id: str
    action: str
    task_id: str
