from .models import Rejection


def problems_for(rec):
    problems = []
    if not rec.task_id:
        problems.append("missing_task_id")
    if "@" not in rec.email:
        problems.append("bad_email")
    if not rec.duration_s:
        problems.append("missing_duration")
    elif rec.duration_s < 0:
        problems.append("negative_duration")
    if rec.submitted is None:
        problems.append("bad_timestamp")
    return problems


def partition(records):
    accepted, rejected = [], []
    for rec in records:
        problems = problems_for(rec)
        if problems:
            rejected.append(Rejection(rec.vendor, rec.row, tuple(problems)))
        else:
            accepted.append(rec)
    return accepted, rejected
