from datetime import timedelta

from .models import State

FAILS_TO_DOWN = 3
OKS_TO_UP = 2
AVAILABILITY_WINDOW = timedelta(minutes=5)


def is_failure(probe):
    return probe.result in ("fail", "timeout")


def apply_probes(workers, probes):
    """Replay the probe log (oldest first) and leave each worker in its final state."""
    by_id = {w.worker_id: w for w in workers}
    fails = {w.worker_id: 0 for w in workers}
    oks = {w.worker_id: 0 for w in workers}
    for probe in probes:
        worker = by_id.get(probe.worker_id)
        if worker is None:
            continue
        if worker.state is State.DRAINING:
            continue
        if is_failure(probe):
            fails[worker.worker_id] += 1
            oks[worker.worker_id] = 0
            if worker.state is not State.DOWN and fails[worker.worker_id] >= FAILS_TO_DOWN:
                worker.state = State.DOWN
        else:
            oks[worker.worker_id] += 1
            fails[worker.worker_id] = 0
            if worker.state is State.DOWN and oks[worker.worker_id] >= OKS_TO_UP:
                worker.state = State.UP


def availability(workers, probes):
    """Share of passing probes per worker over the last five minutes of the log."""
    if not probes:
        return {}
    start = max(p.checked_at for p in probes) - AVAILABILITY_WINDOW
    result = {}
    for worker in workers:
        recent = [p for p in probes if p.worker_id == worker.worker_id and p.checked_at > start]
        if recent:
            passing = sum(1 for p in recent if not is_failure(p))
            result[worker.worker_id] = round(passing / len(recent), 3)
        else:
            result[worker.worker_id] = None
    return result
