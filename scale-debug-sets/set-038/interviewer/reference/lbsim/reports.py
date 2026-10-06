from collections import Counter
from pathlib import Path

from .loader import load_backends, load_probes, load_requests
from .simulate import run

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def summarize(backends, requests, routes):
    routed = [r for r in requests if routes[r.request_id] is not None]
    rejected = len(requests) - len(routed)
    window_ms = max(r.arrival_ms + r.duration_ms for r in requests) - min(r.arrival_ms for r in requests)
    return {
        "routed": len(routed),
        "rejected": rejected,
        "reject_rate": round(rejected / len(requests), 3),
        "by_pool": dict(sorted(Counter(r.pool for r in routed).items())),
        "utilization": {
            b.id: round(b.busy_ms / (window_ms * b.max_conns), 3)
            for b in sorted(backends.values(), key=lambda b: b.id) if b.served
        },
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    backends = load_backends(data_dir / "backends.json")
    requests = load_requests(data_dir / "requests.csv")
    probes = load_probes(data_dir / "health.csv")
    routes = run(backends, requests, probes)
    return {
        "routes": routes,
        "backends": {b.id: {"served": b.served, "peak": b.peak, "busy_ms": b.busy_ms}
                     for b in sorted(backends.values(), key=lambda b: b.id)},
        "summary": summarize(backends, requests, routes),
    }
