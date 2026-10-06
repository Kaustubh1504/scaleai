from .timeutil import clean


def norm_job(value):
    return clean(value).upper()


def parse_deps(raw):
    return [norm_job(part) for part in clean(raw).split(";") if part.strip()]


def resolve_deps(jobs):
    """Drop dependencies on ids that are not accepted jobs."""
    known = {job.id for job in jobs}
    return {job.id: tuple(d for d in job.depends_on if d in known) for job in jobs}


def blocked_by_failure(job, states):
    return any(states[d].state in ("failed", "blocked") for d in job.depends_on)


def deps_done(job, states):
    return all(states[d].state == "succeeded" for d in job.depends_on)
