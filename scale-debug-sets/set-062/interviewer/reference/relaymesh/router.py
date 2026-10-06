"""Replay the request log against the worker pool (weighted least-inflight)."""
from __future__ import annotations

from relaymesh.health import HealthFeed
from relaymesh.models import ACCEPTING, WorkerState


def release_finished(workers, now_ms: int) -> None:
    for w in workers:
        w.inflight = [end for end in w.inflight if end > now_ms]


def effective_weight(worker) -> float:
    if worker.state is WorkerState.DEGRADED:
        return worker.weight / 2
    return worker.weight


def has_room(worker) -> bool:
    return worker.state in ACCEPTING and len(worker.inflight) < worker.max_inflight


def pick_worker(pool):
    eligible = [w for w in pool if has_room(w)]
    if not eligible:
        return None
    return min(eligible, key=lambda w: (len(w.inflight) / effective_weight(w), w.worker_id))


def replay(workers, requests, events) -> dict[str, str | None]:
    """request_id -> worker_id (None when rejected). Mutates worker state."""
    feed = HealthFeed(events, workers)
    by_zone: dict[str, list] = {}
    for w in workers:
        by_zone.setdefault(w.zone, []).append(w)
    assignments = {}
    for req in requests:
        feed.apply_due(req.arrival_ms)
        release_finished(workers, req.arrival_ms)
        chosen = pick_worker(by_zone.get(req.zone, []))
        if chosen is None:
            assignments[req.request_id] = None
            continue
        chosen.inflight.append(req.end_ms)
        assignments[req.request_id] = chosen.worker_id
    feed.flush()
    return assignments
