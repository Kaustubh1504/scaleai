"""What the pool remembers about each job and each worker."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

QUEUED, DONE, FAILED = "queued", "done", "failed"


@dataclass
class JobRecord:
    id: str
    payload: Any
    pinned_worker: str | None = None
    status: str = QUEUED
    attempts: int = 0  # every process() call, whatever the outcome
    failures: int = 0  # attempts that raised TaskFailedError; these count toward max_attempts
    worker_id: str | None = None  # worker of the most recent attempt
    result: Any = None
    error: str | None = None
    not_before: float = float("-inf")  # backoff: not eligible while clock.time() < not_before
    lost_on: set[str] = field(default_factory=set)  # workers that died or hung while running this job
    history: list[dict] = field(default_factory=list)  # one entry per process() call that raised

    def view(self) -> dict:
        return {"id": self.id, "status": self.status, "attempts": self.attempts, "worker_id": self.worker_id,
                "result": self.result, "error": self.error}


@dataclass
class Member:
    """A registered worker, as the pool sees it (never the worker's own state)."""

    worker: Any
    seq: int  # registration order
    last_heard: float  # registration time or the last valid heartbeat, on the pool's clock
    failed: bool = False  # a send hit WorkerUnreachable/Timeout; cleared by the next heartbeat
    sent: int = 0  # process() calls made to this worker

    @property
    def id(self) -> str:
        return self.worker.worker_id

    def is_up(self, now: float, heartbeat_timeout_s: float) -> bool:
        return not self.failed and now - self.last_heard <= heartbeat_timeout_s
