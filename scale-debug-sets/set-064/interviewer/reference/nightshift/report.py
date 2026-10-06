"""Run every queue and build the nightly report."""
from __future__ import annotations

from nightshift.dispatcher import run_queue
from nightshift.loader import load_config, load_jobs, load_outcomes
from nightshift.timeutil import clock, minutes_between


def wait_minutes(job) -> int | None:
    if job.first_start is None:
        return None
    return minutes_between(job.submitted_at, job.first_start)


def is_late(job) -> bool:
    return job.deadline is not None and job.finished_at is not None and job.finished_at > job.deadline


def build_report() -> dict:
    config = load_config()
    jobs = load_jobs(config["run_start"])
    outcomes = load_outcomes()
    logs = {}
    for queue in sorted({j.queue for j in jobs}):
        members = [j for j in jobs if j.queue == queue]
        logs[queue] = run_queue(
            queue, members, config["slots"].get(queue, 1), config["run_start"], config["backoff_min"], outcomes
        )
    job_rows = {
        j.job_id: {
            "queue": j.queue,
            "status": j.status,
            "attempts": j.attempts,
            "first_start": clock(j.first_start),
            "finished": clock(j.finished_at),
            "wait_min": wait_minutes(j),
        }
        for j in sorted(jobs, key=lambda j: j.job_id)
    }
    return {
        "jobs": job_rows,
        "summary": {
            "attempts_by_queue": {q: len(log.entries) for q, log in logs.items()},
            "late_jobs": sorted(j.job_id for j in jobs if is_late(j)),
        },
    }
