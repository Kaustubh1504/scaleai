def missing_dep(job, jobs):
    """First dependency (in listed order) that is not a known job, else None."""
    for dep in job.deps:
        if dep not in jobs:
            return dep
    return None


# VERIFIED
def cycle_members(jobs):
    """Ids of jobs that sit on a dependency cycle (deps to unknown jobs are ignored)."""
    on_cycle, state = set(), {}

    def visit(job_id, path):
        state[job_id] = "open"
        path.append(job_id)
        for dep in jobs[job_id].deps:
            if dep not in jobs:
                continue
            if state.get(dep) == "open":
                on_cycle.update(path[path.index(dep):])
            elif dep not in state:
                visit(dep, path)
        path.pop()
        state[job_id] = "done"

    for job_id in sorted(jobs):
        if job_id not in state:
            visit(job_id, [])
    return on_cycle


def blocked_jobs(jobs):
    """{job_id: reason} for jobs that can never be scheduled."""
    blocked = {}
    cycles = cycle_members(jobs)
    for job_id, job in jobs.items():
        dep = missing_dep(job, jobs)
        if dep is not None:
            blocked[job_id] = f"missing_dep:{dep}"
        elif job_id in cycles:
            blocked[job_id] = "cycle"
    return blocked
