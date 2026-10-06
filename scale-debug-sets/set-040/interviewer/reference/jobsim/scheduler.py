from .models import JobState
from .timeparse import fmt_clock

RETRY_DELAY = 10


def _deps_done(state, states):
    return all(d in states and states[d].status == "succeeded" for d in state.job.deps)


def _finish(state, failures, now):
    if state.attempts in failures.get(state.job.job_id, ()):
        state.log(f"fail@{fmt_clock(now)}")
        if state.attempts <= state.job.max_retries:
            state.status = "pending"
            state.ready_at = now + RETRY_DELAY
        else:
            state.status = "failed"
    else:
        state.log(f"done@{fmt_clock(now)}")
        state.status = "succeeded"


def simulate(jobs, failures, workers, blocked):
    """Run the day minute by minute (event to event). Returns {job_id: JobState}."""
    states = {job_id: JobState(job) for job_id, job in jobs.items()}
    for job_id in blocked:
        states[job_id].status = "blocked"
    free = [f"w{i}" for i in range(1, workers + 1)]
    running, queue = [], []
    now = min(s.ready_at for s in states.values() if s.status == "pending")
    while True:
        for state in sorted((s for s in running if s.end <= now), key=lambda s: (s.end, s.worker)):
            running.remove(state)
            free.append(state.worker)
            _finish(state, failures, now)
        free.sort()

        for state in states.values():
            if (state.status == "pending" and state not in queue
                    and state.ready_at <= now and _deps_done(state, states)):
                queue.append(state)
        queue.sort(key=lambda s: s.job.queue_key())

        for state in list(queue):
            if not free:
                break
            state.worker = free.pop(0)
            state.status = "running"
            state.attempts += 1
            state.start, state.end = now, now + state.job.duration
            state.busy += state.job.duration
            state.log(f"start@{fmt_clock(now)}/{state.worker}")
            running.append(state)
            queue.remove(state)

        upcoming = [s.end for s in running]
        upcoming += [s.ready_at for s in states.values() if s.status == "pending" and s.ready_at > now]
        if not upcoming:
            break
        now = min(upcoming)

    for state in states.values():
        if state.status == "pending":
            state.status = "skipped"
    return states
