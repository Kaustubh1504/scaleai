from datetime import timedelta
from pathlib import Path

from .loader import load_config, load_jobs, load_outcomes, load_workers
from .pools import capacity, pool_names
from .simulator import simulate
from .timeutil import clock

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def wait_minutes(job, state, day_start):
    started = day_start + timedelta(minutes=state.first_start)
    return int((started - job.submitted_at).total_seconds() // 60)


def longest_wait(jobs, states, day_start):
    waits = [(wait_minutes(job, states[job.id], day_start), job.id)
             for job in jobs if states[job.id].first_start is not None]
    if not waits:
        return None
    minutes, jid = min(waits, key=lambda w: (-w[0], w[1]))
    return {"job": jid, "minutes": minutes}


def pool_report(workers, runs, makespan):
    slots = capacity(workers)
    out = {}
    for pool in pool_names(workers):
        busy = sum(r.end - r.start for r in runs if r.pool == pool)
        cap = slots[pool] * makespan
        out[pool] = {
            "slots": slots[pool],
            "busy_minutes": busy,
            "utilization": round(100 * busy / cap, 1) if cap else 0.0,
        }
    return out


def build_schedule(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    workers = load_workers(data_dir / "workers.csv")
    jobs, rejected = load_jobs(data_dir / "jobs.csv", set(pool_names(workers)))
    outcomes = load_outcomes(data_dir / "attempts.csv")
    states, runs = simulate(jobs, workers, outcomes, config)
    day_start = config["day_start"]
    finished = [s.finished_at for s in states.values() if s.finished_at is not None]
    makespan = max(finished, default=0)
    return {
        "intake": {
            job.id: {"pool": job.pool, "priority": job.priority, "duration": job.duration,
                     "depends_on": list(job.depends_on)}
            for job in jobs
        },
        "rejected": rejected,
        "jobs": {
            job.id: {
                "state": states[job.id].state,
                "attempts": states[job.id].attempts,
                "worker": states[job.id].worker,
                "start": clock(day_start, states[job.id].first_start),
                "end": clock(day_start, states[job.id].finished_at),
            }
            for job in jobs
        },
        "report": {
            "makespan_minutes": makespan,
            "pools": pool_report(workers, runs, makespan),
            "longest_wait": longest_wait(jobs, states, day_start),
        },
    }
