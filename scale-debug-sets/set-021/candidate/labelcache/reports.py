import json
from pathlib import Path

from .loader import load_config, load_requests
from .service import replay
from .utils import iso

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    default_ttl, ttls = load_config(data_dir / "config.json")
    requests = load_requests(data_dir / "requests.csv")
    outcomes, stats, cache, backend = replay(requests, default_ttl, ttls)

    if requests:
        cache.purge_expired(requests[-1].ts)
    snapshot = sorted(cache.entries(), key=lambda e: (e.model, e.task_id, e.locale))

    return {
        "outcomes": [
            {"ts": iso(req.ts), "task_id": req.task_id, "model": req.model,
             "locale": req.locale, "result": result, "value": value}
            for req, result, value in outcomes
        ],
        "models": {
            model: {
                "hits": s.hits,
                "misses": s.misses,
                "version": backend.version(model),
                "last_refresh": s.last_refresh,
            }
            for model, s in sorted(stats.items())
        },
        "snapshot": [
            {"task_id": e.task_id, "model": e.model, "locale": e.locale,
             "value": e.value, "expires_at": iso(e.expires_at)}
            for e in snapshot
        ],
    }


def report_json(data_dir=DATA_DIR):
    return json.dumps(build_report(data_dir), indent=2, sort_keys=True, default=str)
