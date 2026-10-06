from collections import Counter
from pathlib import Path

from .loader import load_clients, load_invalidations, load_prices, load_requests, load_ttls
from .replay import replay

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def summarize(requests, responses, origin):
    outcomes = Counter(r.outcome for r in responses)
    looked_up = outcomes["hit"] + outcomes["miss"]
    first = min(r.ts for r in requests)
    last = max(r.ts for r in requests)
    span_hours = (last - first).seconds / 3600
    return {
        "requests": len(responses),
        "hits": outcomes["hit"],
        "misses": outcomes["miss"],
        "errors": outcomes["error"],
        "hit_rate": round(outcomes["hit"] / looked_up, 3) if looked_up else 0.0,
        "origin_calls": dict(sorted(Counter(origin.calls).items())),
        "span_hours": round(span_hours, 2),
        "requests_per_hour": round(len(responses) / span_hours, 2) if span_hours else 0.0,
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    requests = load_requests(data_dir / "requests.csv")
    responses, origin = replay(
        requests,
        load_invalidations(data_dir / "invalidations.csv"),
        load_ttls(data_dir / "ttl.json"),
        load_prices(data_dir / "prices.csv"),
        load_clients(data_dir / "clients.csv"),
    )
    return {
        "responses": {r.req_id: {"outcome": r.outcome, "price": r.price} for r in responses},
        "summary": summarize(requests, responses, origin),
    }
