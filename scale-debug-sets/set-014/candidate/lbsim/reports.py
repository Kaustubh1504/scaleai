from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from .health import apply_probes, availability
from .loader import load_probes, load_requests, load_workers
from .router import route

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def peak_in_flight(requests, assignments):
    events = []
    for req in requests:
        if req.request_id in assignments:
            events.append((req.arrived_at, 1))
            events.append((req.arrived_at + timedelta(milliseconds=req.duration_ms), -1))
    events.sort(key=lambda e: (e[0], -e[1]))
    peak = current = 0
    for _, delta in events:
        current += delta
        peak = max(peak, current)
    return peak


def zone_summary(workers, requests, assignments):
    zone_of = {w.worker_id: w.zone for w in workers}
    served = defaultdict(int)
    for worker in workers:
        served[worker.zone] += len(worker.served)
    durations = defaultdict(list)
    for req in requests:
        if req.request_id in assignments:
            durations[zone_of[assignments[req.request_id]]].append(req.duration_ms)
    return {
        zone: {
            "served": served[zone],
            "mean_duration_ms": round(sum(durations[zone]) // len(durations[zone]), 1) if durations[zone] else None,
        }
        for zone in sorted(served)
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    workers = load_workers(data_dir / "workers.json")
    probes = load_probes(data_dir / "probes.csv")
    requests = load_requests(data_dir / "requests.csv")
    apply_probes(workers, probes)
    assignments, rejected = route(workers, requests)
    return {
        "workers": {w.worker_id: w.state.value for w in workers},
        "availability": availability(workers, probes),
        "assignments": assignments,
        "rejected": rejected,
        "peak_in_flight": peak_in_flight(requests, assignments),
        "zones": zone_summary(workers, requests, assignments),
    }
