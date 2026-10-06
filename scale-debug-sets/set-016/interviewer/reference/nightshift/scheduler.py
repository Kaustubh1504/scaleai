from .models import DEAD, PENDING, SKIPPED, SUCCEEDED


def ready_jobs(jobs):
    done = {j.job_id for j in jobs.values() if j.status == SUCCEEDED}
    ready = [j for j in jobs.values() if j.status == PENDING and all(d in done for d in j.depends_on)]
    # most urgent first, then oldest submission
    return sorted(ready, key=lambda j: (-j.priority, j.submitted_at, j.job_id))


def skip_dependents(jobs, failed_id):
    skipped = []
    for job in jobs.values():
        if job.status == PENDING and failed_id in job.depends_on:
            job.status = SKIPPED
            skipped.append(job.job_id)
            skipped.extend(skip_dependents(jobs, job.job_id))
    return skipped


def run_attempt(job, outcomes, round_no):
    job.attempts += 1
    outcome = outcomes.get((job.job_id, job.attempts), "ok")
    job.history.append(outcome)
    if outcome == "ok":
        job.status = SUCCEEDED
        job.finished_round = round_no
    elif not job.can_retry():
        job.status = DEAD
        job.finished_round = round_no


def run_schedule(jobs, outcomes, workers):
    rounds = []
    while True:
        batch = ready_jobs(jobs)[:workers]
        if not batch:
            break
        round_no = len(rounds) + 1
        for job in batch:
            run_attempt(job, outcomes, round_no)
            if job.status == DEAD:
                skip_dependents(jobs, job.job_id)
        rounds.append([j.job_id for j in batch])
    return rounds
