import csv

from .models import Job
from .utils import clean, norm_id, parse_bool, parse_timestamp, split_ids


def load_jobs(path, default_max_retries):
    jobs = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if not parse_bool(row["enabled"]):
                continue
            retries = clean(row["max_retries"])
            job = Job(
                job_id=norm_id(row["job_id"]),
                name=clean(row["name"]),
                priority=int(clean(row["priority"])),
                depends_on=split_ids(row["depends_on"]),
                max_retries=int(retries) if retries else default_max_retries,
                submitted_at=parse_timestamp(row["submitted_at"]),
                duration_s=int(clean(row["duration_s"])),
            )
            jobs[job.job_id] = job
    return jobs


def load_outcomes(path):
    """(job_id, attempt number) -> "ok" or "fail". Attempts with no row succeed."""
    outcomes = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (norm_id(row["job_id"]), int(clean(row["attempt"])))
            outcomes[key] = clean(row["outcome"]).lower()
    return outcomes
