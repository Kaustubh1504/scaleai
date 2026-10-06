import csv
import json
from dataclasses import replace

from .deps import norm_job, parse_deps, resolve_deps
from .models import Job, Worker
from .timeutil import clean, parse_duration, parse_time

DEFAULT_RETRIES = 2


def norm(value):
    return clean(value).lower()


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        "day_start": parse_time(raw["day_start"]),
        "horizon": parse_duration(raw["horizon"]),
        "backoff": parse_duration(raw["retry_backoff"]),
    }


def load_workers(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return [Worker(norm(r["worker_id"]), norm(r["pool"]), norm(r["status"]) == "active")
                for r in csv.DictReader(fh)]


def load_jobs(path, pools):
    jobs, rejected = [], {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            jid = norm_job(row["job_id"])
            pool = norm(row["pool"])
            if pool not in pools:
                rejected[jid] = "unknown_pool"
                continue
            retries = clean(row["max_retries"])
            jobs.append(Job(
                id=jid,
                pool=pool,
                priority=int(clean(row["priority"])),
                submitted_at=parse_time(row["submitted_at"]),
                duration=parse_duration(row["duration"]),
                max_retries=int(retries or 0) or DEFAULT_RETRIES,
                depends_on=tuple(parse_deps(row["depends_on"])),
                owner=norm(row["owner"]),
            ))
    resolved = resolve_deps(jobs)
    return [replace(job, depends_on=resolved[job.id]) for job in jobs], rejected


def load_outcomes(path):
    """(job id, attempt number) -> 'ok' or 'fail'."""
    outcomes = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            outcomes[(norm_job(row["job_id"]), int(row["attempt"]))] = norm(row["outcome"])
    return outcomes
