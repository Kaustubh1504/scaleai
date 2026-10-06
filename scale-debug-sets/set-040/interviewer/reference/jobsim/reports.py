import json
from itertools import groupby
from pathlib import Path

from .dag import blocked_jobs
from .loader import load_failures, load_jobs
from .scheduler import simulate
from .timeparse import fmt_clock

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def team_summary(states):
    summary = {}
    ordered = sorted(states.values(), key=lambda s: s.job.team)
    for team, group in groupby(ordered, key=lambda s: s.job.team):
        members = list(group)
        summary[team] = {
            "jobs": len(members),
            "succeeded": sum(1 for s in members if s.status == "succeeded"),
            "busy_min": sum(s.busy for s in members),
        }
    return summary


def late_jobs(states):
    return sorted(s.job.job_id for s in states.values()
                  if s.status == "succeeded" and s.job.deadline is not None and s.end > s.job.deadline)


def utilization(states, workers):
    ran = [s for s in states.values() if s.attempts]
    if not ran:
        return None
    span = max(s.end for s in ran) - min(s.start for s in ran)
    return round(sum(s.busy for s in ran) / (workers * span), 3)


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    with open(data_dir / "config.json", encoding="utf-8") as fh:
        workers = int(json.load(fh)["workers"])
    jobs = load_jobs(data_dir / "jobs.csv")
    blocked = blocked_jobs(jobs)
    states = simulate(jobs, load_failures(data_dir / "failures.csv"), workers, blocked)
    return {
        "jobs": {
            job_id: {"status": s.status, "attempts": s.attempts, "start": fmt_clock(s.start),
                     "end": fmt_clock(s.end), "worker": s.worker}
            for job_id, s in sorted(states.items())
        },
        "events": {job_id: s.events for job_id, s in sorted(states.items()) if s.events},
        "blocked": dict(sorted(blocked.items())),
        "summary": {
            "teams": team_summary(states),
            "late": late_jobs(states),
            "utilization": utilization(states, workers),
        },
    }
