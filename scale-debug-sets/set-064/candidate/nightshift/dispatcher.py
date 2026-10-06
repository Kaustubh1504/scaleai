"""Minute-by-minute simulation of one queue."""
from __future__ import annotations

from datetime import timedelta

from nightshift.models import QueueLog
from nightshift.retry import next_ready_at, should_retry
from nightshift.timeutil import plus_minutes

HORIZON_MIN = 24 * 60


def dispatch_order(ready):
    # most urgent first, then oldest submission, then id
    return sorted(ready, key=lambda j: (-j.priority, j.submitted_at, j.job_id))


def deps_done(job, by_id) -> bool:
    return all(dep in by_id and by_id[dep].status == "done" for dep in job.depends_on)


def run_queue(name, jobs, slots, run_start, backoff_min, outcomes) -> QueueLog:
    log = QueueLog(name)
    by_id = {j.job_id: j for j in jobs}
    for j in jobs:
        j.ready_at = max(j.submitted_at, run_start)
    running = []  # (finish time, job)
    for minute in range(HORIZON_MIN + 1):
        now = run_start + timedelta(minutes=minute)
        for finish, job in [item for item in running if item[0] <= now]:
            running.remove((finish, job))
            outcome = outcomes.get((job.job_id, job.attempts), "ok")
            log.record(job.job_id, job.attempts, outcome)
            if outcome == "ok":
                job.status, job.finished_at = "done", finish
            elif should_retry(job):
                job.status, job.ready_at = "pending", next_ready_at(finish, job.attempts, backoff_min)
            else:
                job.status = "failed"
        ready = [
            j for j in jobs
            if j.status == "pending" and j.ready_at <= now and deps_done(j, by_id)
        ]
        for job in dispatch_order(ready)[: slots - len(running)]:
            job.status = "running"
            job.attempts += 1
            if job.first_start is None:
                job.first_start = now
            running.append((plus_minutes(now, job.duration_min), job))
    for j in jobs:
        if j.status == "pending":
            j.status = "blocked"
    return log
