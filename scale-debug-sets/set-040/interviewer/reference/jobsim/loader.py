import csv

from .models import Job
from .timeparse import parse_clock, parse_duration


def _clean(value):
    return (value or "").strip().lower()


def load_jobs(path):
    jobs = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            job = Job(
                job_id=_clean(row["job_id"]),
                team=_clean(row["team"]),
                priority=int(row["priority"]),
                release=parse_clock(row["release"]),
                duration=parse_duration(row["duration"]),
                deps=tuple(d for d in (_clean(x) for x in (row["deps"] or "").split(";")) if d),
                deadline=parse_clock(row["deadline"]),
                max_retries=int(row["max_retries"].strip() or 0),
            )
            jobs[job.job_id] = job
    return jobs


def load_failures(path):
    """{job_id: {attempt numbers that fail}}"""
    failures = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            failures.setdefault(_clean(row["job_id"]), set()).add(int(row["attempt"]))
    return failures
