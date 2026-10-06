from datetime import timedelta

from .models import State


# VERIFIED
def release_finished(workers, now):
    for worker in workers:
        worker.active = [end for end in worker.active if end > now]


def pick_worker(workers, zone):
    eligible = [w for w in workers if w.state is State.UP and len(w.active) < w.max_conns]
    pool = [w for w in eligible if w.zone == zone] or eligible
    if not pool:
        return None
    return min(pool, key=lambda w: (len(w.active) / w.weight, w.worker_id))


def route(workers, requests):
    """Returns ({request_id: worker_id}, [rejected request ids]) in arrival order."""
    assignments, rejected = {}, []
    for req in requests:
        release_finished(workers, req.arrived_at)
        worker = pick_worker(workers, req.zone)
        if worker is None:
            rejected.append(req.request_id)
            continue
        worker.active.append(req.arrived_at + timedelta(milliseconds=req.duration_ms))
        worker.served.append(req.request_id)
        assignments[req.request_id] = worker.worker_id
    return assignments, rejected
