import asyncio
from pathlib import Path

from .client import BatchClient
from .config import load_config
from .loader import load_requests
from .pipeline import run_all

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def request_rows(shards, skipped, outcomes):
    rows = {}
    for shard, items in shards.items():
        outcome = outcomes[shard]
        for item in items:
            if outcome.status != "completed":
                rows[item["id"]] = {"shard": shard, "status": outcome.status, "label": None, "score": None}
            elif item["id"] in outcome.results:
                rows[item["id"]] = {"shard": shard, **outcome.results[item["id"]]}
            else:
                rows[item["id"]] = {"shard": shard, "status": "missing", "label": None, "score": None}
    for shard, rid in skipped:
        rows[rid] = {"shard": shard, "status": "skipped", "label": None, "score": None}
    return dict(sorted(rows.items()))


def summarize(outcomes, config):
    tokens = sum(o.tokens for o in outcomes.values())
    return {
        "shards": {shard: o.status for shard, o in sorted(outcomes.items())},
        "total_tokens": tokens,
        "cost_usd": round(tokens / 1000) * config.price_per_1k_tokens,
    }


def build_report(base_url, api_key, data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    shards, skipped = load_requests(data_dir / "requests.csv")
    client = BatchClient(base_url, api_key, config)
    outcomes = asyncio.run(run_all(client, shards))
    return {"requests": request_rows(shards, skipped, outcomes), "summary": summarize(outcomes, config)}
