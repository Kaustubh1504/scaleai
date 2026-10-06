from collections import Counter
from pathlib import Path

from .config import load_config
from .loader import load_jobs, load_outcomes
from .models import DEAD, PENDING, SKIPPED, SUCCEEDED
from .scheduler import run_schedule

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATUSES = (SUCCEEDED, DEAD, SKIPPED, PENDING)


def summarize(jobs):
    counts = Counter(j.status for j in jobs.values())
    ran = [j for j in jobs.values() if j.attempts > 0]
    total_attempts = sum(j.attempts for j in ran)
    busy_seconds = sum(j.attempts * j.duration_s for j in ran)
    return {
        "counts": {s: counts.get(s, 0) for s in STATUSES},
        "total_attempts": total_attempts,
        "mean_attempts": round(total_attempts / len(ran), 2) if ran else None,
        "busy_minutes": round(busy_seconds / 60, 1),
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    jobs = load_jobs(data_dir / "jobs.csv", config.default_max_retries)
    outcomes = load_outcomes(data_dir / "attempts.csv")
    rounds = run_schedule(jobs, outcomes, config.workers)
    return {
        "rounds": rounds,
        "jobs": {
            j.job_id: {"status": j.status, "attempts": j.attempts, "finished_round": j.finished_round}
            for j in sorted(jobs.values(), key=lambda j: j.job_id)
        },
        "summary": summarize(jobs),
    }
