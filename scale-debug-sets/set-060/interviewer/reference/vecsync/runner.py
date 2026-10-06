import asyncio
from pathlib import Path

from .client import EmbeddingClient, UpsertError
from .config import load_config
from .dataset import fetch_all, select

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def make_batches(records, size):
    return [(f"b{n}", records[i:i + size]) for n, i in enumerate(range(0, len(records), size), start=1)]


async def commit(client, results):
    ok = [r for r in results if r.status == "ok"]
    outcomes = await asyncio.gather(*(client.upsert(r) for r in ok), return_exceptions=True)
    committed, failed = [], []
    for result, outcome in zip(ok, outcomes):
        if isinstance(outcome, UpsertError):
            failed.append(result.batch_id)
        elif isinstance(outcome, BaseException):
            raise outcome
        else:
            committed.append(outcome)
    return committed, failed


async def run(base_url, api_key, data_dir=DATA_DIR):
    config = load_config(Path(data_dir) / "config.json")
    client = EmbeddingClient(base_url, api_key, config)
    raw, pages = await fetch_all(client)
    records = select(raw, config.since)
    batches = make_batches(records, config.batch_size)
    results = await asyncio.gather(*(client.embed_batch(bid, recs) for bid, recs in batches))
    try:
        committed, failed = await commit(client, results)
    except UpsertError as err:
        committed, failed = [], [err.batch_id]
    return {
        "fetched": len(raw),
        "pages": pages,
        "selected": [r["id"] for r in records],
        "batches": {r.batch_id: {"status": r.status, "http_status": r.http_status,
                                 "attempts": r.attempts, "records": r.record_ids} for r in results},
        "vectors": {rid: vec for r in results if r.status == "ok" for rid, vec in zip(r.record_ids, r.vectors)},
        "total_tokens": sum(r.tokens for r in results),
        "commit": {"committed": sorted(committed), "failed": sorted(failed)},
    }


def build_report(base_url, api_key, data_dir=DATA_DIR):
    return asyncio.run(run(base_url, api_key, data_dir))
