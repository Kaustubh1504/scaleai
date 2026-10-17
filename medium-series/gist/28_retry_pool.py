# 28. Run jobs with retries and a dead-letter list
# Standalone: copy this file as-is. Deps: stdlib

import time
from concurrent.futures import ThreadPoolExecutor


def run_jobs(jobs, handler, workers: int = 5, max_attempts: int = 3, backoff: float = 0.0,
             retryable=lambda error: True):
    """handler(job) for each job, `workers` at a time. A job that raises is retried (max_attempts total)
    while retryable(error); then it goes to the dead-letter list.
    Returns (results in input order with None for dead jobs, dead_letters)."""
    dead = []

    def run(job):
        for attempt in range(1, max_attempts + 1):
            try:
                return handler(job)
            except Exception as e:
                if attempt == max_attempts or not retryable(e):
                    dead.append({"job": job, "error": f"{type(e).__name__}: {e}", "attempts": attempt})
                    return None
                time.sleep(backoff * 2 ** (attempt - 1))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(run, jobs))
    return results, dead
