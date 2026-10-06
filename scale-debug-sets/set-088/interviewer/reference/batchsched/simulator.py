from .deps import blocked_by_failure, deps_done
from .models import JobState, Run
from .pools import PoolTable
from .retry import backoff_delay, should_retry
from .timeutil import to_offset


def queue_key(job, submit_offset):
    # most urgent first, then oldest submission, then id
    return (-job.priority, submit_offset[job.id], job.id)


def simulate(jobs, workers, outcomes, config):
    day_start, horizon, backoff = config["day_start"], config["horizon"], config["backoff"]
    by_id = {job.id: job for job in jobs}
    submit = {job.id: max(0, to_offset(day_start, job.submitted_at)) for job in jobs}
    states = {job.id: JobState() for job in jobs}
    table = PoolTable(workers)
    running = {}  # job id -> (worker id, start, end)
    runs = []

    for t in range(horizon + 1):
        for jid in sorted(j for j, (_, _, end) in running.items() if end == t):
            worker_id, start, end = running.pop(jid)
            table.release(worker_id)
            runs.append(Run(jid, by_id[jid].pool, worker_id, start, end))
            state = states[jid]
            if outcomes.get((jid, state.attempts), "ok") == "ok":
                state.state, state.finished_at = "succeeded", t
            elif should_retry(state.attempts, by_id[jid].max_retries):
                state.state, state.ready_at = "queued", t + backoff_delay(state.attempts, backoff)
            else:
                state.state, state.finished_at = "failed", t

        changed = True
        while changed:
            changed = False
            for job in jobs:
                if states[job.id].state == "queued" and blocked_by_failure(job, states):
                    states[job.id].state = "blocked"
                    changed = True

        eligible = [job for job in jobs
                    if states[job.id].state == "queued" and submit[job.id] <= t
                    and states[job.id].ready_at <= t and deps_done(job, states)]
        for job in sorted(eligible, key=lambda j: queue_key(j, submit)):
            worker = table.free_worker(job.pool)
            if worker is None:
                continue
            table.assign(worker, job.id)
            state = states[job.id]
            state.state = "running"
            state.attempts += 1
            state.worker = worker.id
            if state.first_start is None:
                state.first_start = t
            running[job.id] = (worker.id, t, t + job.duration)

    for state in states.values():
        if state.state in ("queued", "running"):
            state.state = "pending"
    return states, runs
