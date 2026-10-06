"""Retry policy: how many attempts a job gets and when it may run again."""
from __future__ import annotations

from nightshift.timeutil import plus_minutes


def should_retry(job) -> bool:
    """Called after a failed attempt; job.attempts already counts it."""
    return job.attempts <= job.max_retries


# VERIFIED
def next_ready_at(finished_at, attempt: int, backoff_min: int):
    """Linear backoff: wait backoff_min × (attempt number that just failed)."""
    return plus_minutes(finished_at, backoff_min * attempt)
