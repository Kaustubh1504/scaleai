"""Top-level replay report."""
from __future__ import annotations

from collections import Counter

from relaymesh.loader import load_health, load_requests, load_workers
from relaymesh.models import WorkerState
from relaymesh.router import replay
from relaymesh.stats import worker_stats


def out_of_rotation(workers) -> list[str]:
    return sorted(
        w.worker_id for w in workers
        if w.state is WorkerState.DOWN or w.state is WorkerState.DRAINING
    )


def build_report() -> dict:
    workers = load_workers()
    requests = load_requests()
    events = load_health()
    assignments = replay(workers, requests, events)
    stats = worker_stats(workers, requests, assignments)
    zone_requests = Counter(r.zone for r in requests)
    return {
        "assignments": assignments,
        "workers": stats,
        "summary": {
            "requests_by_zone": dict(sorted(zone_requests.items())),
            "rejected": sorted(rid for rid, wid in assignments.items() if wid is None),
            "out_of_rotation": out_of_rotation(workers),
        },
    }
