from collections import Counter
from pathlib import Path

from .loader import load_backends, load_config, load_health, load_requests
from .metrics import per_backend
from .replay import Replay

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def zone_totals(assignments, backends):
    zones = Counter()
    for bid in assignments.values():
        if bid is not None:
            zones.update(backends[bid].zone)
    return dict(sorted(zones.items()))


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    backends = load_backends(data_dir / "backends.csv", config["pool"])
    requests = load_requests(data_dir / "requests.csv")
    replay = Replay(backends, config).run(requests, load_health(data_dir / "health.csv"))
    return {
        "transitions": [list(t) for t in replay.health.transitions],
        "final_state": {bid: s.value for bid, s in sorted(replay.health.state.items())},
        "assignments": replay.assignments,
        "sessions": dict(sorted(replay.sticky.owner.items())),
        "summary": {
            "backends": per_backend(replay.assignments, requests, backends),
            "zones": zone_totals(replay.assignments, backends),
            "failovers": replay.failovers,
            "rejected": sorted(rid for rid, bid in replay.assignments.items() if bid is None),
        },
    }
