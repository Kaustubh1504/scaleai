"""The job-processing pool: a coordinator that owns a queue of jobs and keeps
a fleet of workers busy.

The pool works in rounds. Each ``tick()`` plans which queued jobs go to which
up worker (least loaded first, at most ``concurrency_per_worker`` per worker
per round), then sends them one at a time. Worker errors drive failover (the
job goes back to the front of the queue and the worker is marked down),
heartbeats drive liveness, and jobs that keep failing are retried with
exponential backoff and finally dead-lettered.

Keep the constructor and the public method signatures: other services (and
the interviewer's tests) call them. PART1.md - PART3.md say what each method
must do.

Not thread-safe: one thread owns a pool and calls all of its methods.
"""

from __future__ import annotations

import copy
import itertools
import logging
from collections import Counter
from typing import Any, Iterable, Protocol

from mock_services.clock import Clock, RealClock
from mock_services.workers import TaskFailedError, WorkerOverloadedError, WorkerTimeoutError, WorkerUnreachableError
from pool.records import DONE, FAILED, QUEUED, JobRecord, Member

__all__ = ["Pool", "Worker"]

log = logging.getLogger("pool")

POISON_WORKER_LOSSES = 2  # a job lost on this many different workers is dead-lettered as poison


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
        self._members: dict[str, Member] = {}  # registration order
        self._jobs: dict[str, JobRecord] = {}  # every job ever submitted
        self._queue: list[str] = []  # ids of queued jobs, front first
        self._results: dict[str, Any] = {}  # completion order
        self._dead_letters: list[dict] = []
        self._seq = itertools.count()
        self._closed = False
        for worker in workers:
            self.add_worker(worker)

    # ------------------------------------------------------------ membership

    def add_worker(self, worker: Worker) -> None:
        if worker.worker_id in self._members:
            raise ValueError(f"worker {worker.worker_id!r} is already registered")
        self._members[worker.worker_id] = Member(worker, next(self._seq), self.clock.time())
        log.info("worker %s joined", worker.worker_id)

    # ------------------------------------------------------------------ jobs

    def submit(self, job_id: str, payload: Any = None, *, pinned_worker: str | None = None) -> bool:
        if self._closed:
            raise RuntimeError("pool is draining; not accepting jobs")
        if not isinstance(job_id, str) or not job_id:
            raise ValueError(f"job id must be a non-empty string, got {job_id!r}")
        existing = self._jobs.get(job_id)
        if existing is not None:
            if existing.payload != payload:
                raise ValueError(f"job {job_id!r} was already submitted with a different payload")
            return False
        self._jobs[job_id] = JobRecord(job_id, copy.deepcopy(payload), pinned_worker)
        self._queue.append(job_id)
        return True

    def tick(self) -> int:
        """Run one round; return the number of worker.process() calls made."""
        plan = self._plan(self.clock.time())
        planned = {job.id for job, _ in plan}
        front: list[str] = []  # failed over: back to the front, in plan order
        back: list[str] = []  # failed and will be retried after a backoff
        skip: set[str] = set()  # workers that failed earlier in this round
        sent = 0
        for job, member in plan:
            if member.id in skip:
                front.append(job.id)
                continue
            sent += 1
            outcome = self._send(job, member)
            if outcome == "retry":
                back.append(job.id)
            elif outcome in ("lost", "refused"):
                skip.add(member.id)
                if job.status == QUEUED:  # not dead-lettered as poison
                    front.append(job.id)
        self._queue = front + [job_id for job_id in self._queue if job_id not in planned] + back
        return sent

    def _plan(self, now: float) -> list[tuple[JobRecord, Member]]:
        up = [m for m in self._members.values() if m.is_up(now, self.heartbeat_timeout_s)]
        load = {m.id: 0 for m in up}
        plan = []
        for job_id in self._queue:
            job = self._jobs[job_id]
            if job.not_before > now:
                continue
            options = [m for m in up if load[m.id] < self.concurrency_per_worker
                       and job.pinned_worker in (None, m.id)]
            if not options:
                continue
            member = min(options, key=lambda m: (load[m.id], m.sent, m.seq))
            load[member.id] += 1
            plan.append((job, member))
        return plan

    def _send(self, job: JobRecord, member: Member) -> str:
        """Send one job; returns "done", "failed", "retry", "lost" or "refused"."""
        job.attempts += 1
        job.worker_id = member.id
        member.sent += 1
        try:
            result = member.worker.process(job.payload, timeout=self.job_timeout_s)
        except TaskFailedError as exc:
            self._note_error(job, member, exc)
            job.failures += 1
            if job.failures >= self.max_attempts:
                self._dead_letter(job, "max_attempts", str(exc))
                return "failed"
            job.not_before = self.clock.time() + self.backoff_base_s * 2 ** (job.failures - 1)
            log.info("job %s failed (%d/%d); retry at %.3f", job.id, job.failures, self.max_attempts, job.not_before)
            return "retry"
        except (WorkerUnreachableError, WorkerTimeoutError) as exc:
            self._note_error(job, member, exc)
            member.failed = True
            job.lost_on.add(member.id)
            log.warning("worker %s down (%s); failing over its jobs", member.id, exc)
            if len(job.lost_on) >= POISON_WORKER_LOSSES:
                self._dead_letter(job, "poison", f"lost on workers {sorted(job.lost_on)}: {exc}")
            return "lost"
        except WorkerOverloadedError as exc:
            self._note_error(job, member, exc)
            log.info("worker %s refused job %s: overloaded", member.id, job.id)
            return "refused"
        job.status, job.result = DONE, result
        self._results[job.id] = result
        return "done"

    def _note_error(self, job: JobRecord, member: Member, exc: Exception) -> None:
        job.history.append({"worker_id": member.id, "error": str(exc) or type(exc).__name__,
                            "at": self.clock.time()})

    def _dead_letter(self, job: JobRecord, reason: str, error: str) -> None:
        job.status, job.error = FAILED, error
        self._dead_letters.append({"job_id": job.id, "payload": job.payload, "reason": reason,
                                   "history": job.history})
        log.warning("job %s dead-lettered (%s): %s", job.id, reason, error)

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
        try:
            return copy.deepcopy(self._jobs[job_id].view())
        except KeyError:
            raise KeyError(f"unknown job {job_id!r}") from None

    def pending(self) -> list[str]:
        return list(self._queue)

    def status(self) -> dict:
        now = self.clock.time()
        counts = Counter(job.status for job in self._jobs.values())
        workers = {m.id: "up" if m.is_up(now, self.heartbeat_timeout_s) else "down" for m in self._members.values()}
        return {"queued": counts[QUEUED], "done": counts[DONE], "failed": counts[FAILED], "workers": workers}

    @property
    def results(self) -> dict[str, Any]:
        return copy.deepcopy(self._results)

    # ------------------------------------------------------- later parts

    def on_heartbeat(self, payload: dict) -> None:
        worker_id = payload.get("worker_id") if isinstance(payload, dict) else None
        member = self._members.get(worker_id) if isinstance(worker_id, str) else None
        if member is None:
            log.debug("ignoring heartbeat %r", payload)
            return
        now = self.clock.time()
        if not member.is_up(now, self.heartbeat_timeout_s):
            log.info("worker %s is back", member.id)
        # Liveness is judged on our clock; the payload's ts comes from the worker's clock.
        member.last_heard, member.failed = now, False

    @property
    def dead_letters(self) -> list[dict]:
        return copy.deepcopy(self._dead_letters)

    def drain(self, max_ticks: int = 100) -> list[str]:
        self._closed = True
        self.run_until_idle(max_ticks)
        left = self.pending()
        if left:
            log.warning("drained with %d job(s) still queued: %s", len(left), left)
        return left
