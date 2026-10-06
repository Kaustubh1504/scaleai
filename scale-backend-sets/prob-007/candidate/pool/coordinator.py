"""The job-processing pool: a coordinator that owns a queue of jobs and keeps
a fleet of workers busy.

Keep the constructor and the public method signatures: other services (and
the interviewer's tests) call them. PART1.md - PART3.md say what each method
must do.

Not thread-safe: one thread owns a pool and calls all of its methods.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Protocol

from mock_services.clock import Clock, RealClock

__all__ = ["Pool", "Worker"]

log = logging.getLogger("pool")


class Worker(Protocol):
    """What the pool needs from a worker. ``mock_services.workers.MockWorker`` implements it."""

    worker_id: str

    def process(self, payload: Any, timeout: float | None = None) -> Any: ...

    def heartbeat(self) -> dict | None: ...


class Pool:
    def __init__(
        self,
        workers: Iterable[Worker] = (),
        clock: Clock | None = None,
        *,
        concurrency_per_worker: int = 2,
        job_timeout_s: float = 2.0,
        heartbeat_timeout_s: float = 3.0,
        max_attempts: int = 3,
        backoff_base_s: float = 1.0,
    ):
        if not isinstance(concurrency_per_worker, int) or concurrency_per_worker < 1:
            raise ValueError(f"concurrency_per_worker must be an integer >= 1, got {concurrency_per_worker!r}")
        if not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError(f"max_attempts must be an integer >= 1, got {max_attempts!r}")
        for name, value in (("job_timeout_s", job_timeout_s), ("heartbeat_timeout_s", heartbeat_timeout_s)):
            if value <= 0:
                raise ValueError(f"{name} must be positive, got {value!r}")
        if backoff_base_s < 0:
            raise ValueError(f"backoff_base_s must be >= 0, got {backoff_base_s!r}")
        self.clock = clock or RealClock()
        self.concurrency_per_worker = concurrency_per_worker
        self.job_timeout_s = job_timeout_s
        self.heartbeat_timeout_s = heartbeat_timeout_s
        self.max_attempts = max_attempts
        self.backoff_base_s = backoff_base_s
        # TODO: your state goes here.
        for worker in workers:
            self.add_worker(worker)

    # ------------------------------------------------------------ membership

    def add_worker(self, worker: Worker) -> None:
        raise NotImplementedError

    # ------------------------------------------------------------------ jobs

    def submit(self, job_id: str, payload: Any = None) -> bool:
        raise NotImplementedError

    def tick(self) -> int:
        """Run one round; return the number of worker.process() calls made."""
        raise NotImplementedError

    def run_until_idle(self, max_ticks: int = 100) -> int:
        """Call tick() until a round sends nothing, or ``max_ticks`` rounds have run. Returns jobs sent."""
        sent = 0
        for _ in range(max_ticks):
            n = self.tick()
            sent += n
            if n == 0:
                break
        return sent

    # ----------------------------------------------------------- inspection

    def job(self, job_id: str) -> dict:
        raise NotImplementedError

    def pending(self) -> list[str]:
        raise NotImplementedError

    def status(self) -> dict:
        raise NotImplementedError

    @property
    def results(self) -> dict[str, Any]:
        raise NotImplementedError

    # ------------------------------------------------------- later parts

    def on_heartbeat(self, payload: dict) -> None:
        raise NotImplementedError

    @property
    def dead_letters(self) -> list[dict]:
        raise NotImplementedError

    def drain(self, max_ticks: int = 100) -> list[str]:
        raise NotImplementedError
