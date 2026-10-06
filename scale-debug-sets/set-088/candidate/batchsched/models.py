from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Job:
    id: str
    pool: str
    priority: int
    submitted_at: datetime
    duration: int
    max_retries: int
    depends_on: tuple
    owner: str


@dataclass(frozen=True)
class Worker:
    id: str
    pool: str
    active: bool


@dataclass
class JobState:
    state: str = "queued"
    attempts: int = 0
    ready_at: int = 0
    worker: str | None = None
    first_start: int | None = None
    finished_at: int | None = None


@dataclass(frozen=True)
class Run:
    job_id: str
    pool: str
    worker: str
    start: int
    end: int
