import asyncio
from collections import Counter
from pathlib import Path

from .config import load_config
from .documents import load_documents, load_retired
from .sync import run_sync

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def summarize(result, config):
    counts = Counter(result.outcomes.values())
    return {
        "counts": {status: counts.get(status, 0) for status in ("embedded", "skipped", "failed")},
        "failed_batches": dict(sorted(result.errors.items())),
        "total_tokens": result.total_tokens,
        "cost_usd": round(result.total_tokens // 1000 * config.price_per_1k_tokens, 4),
    }


def build_report(base_url, api_key, data_dir=None, sleep=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    docs = load_documents(data_dir / "documents.csv")
    retired = load_retired(data_dir / "retired.csv", config.as_of)
    result = asyncio.run(run_sync(base_url, api_key, config, docs, retired, sleep=sleep))
    return {
        "outcomes": dict(sorted(result.outcomes.items())),
        "embeddings": dict(sorted(result.embeddings.items())),
        "to_delete": result.to_delete,
        "summary": summarize(result, config),
    }
