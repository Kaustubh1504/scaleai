import asyncio
from pathlib import Path

from .client import EmbeddingClient
from .config import load_config
from .loader import load_documents
from .pipeline import run_pipeline
from .similarity import near_duplicates

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def summarize(run, config):
    embedded = len(run.vectors)
    return {
        "documents": len(run.docs),
        "embedded": embedded,
        "total_tokens": run.total_tokens,
        "tokens_per_doc": run.total_tokens // embedded if embedded else None,
        "near_duplicates": near_duplicates(run.vectors, config.similarity_threshold),
    }


async def build_report_async(base_url, api_key, data_dir=None, sleep=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    kwargs = {"sleep": sleep} if sleep is not None else {}
    client = EmbeddingClient(base_url, api_key, config, **kwargs)
    run = await run_pipeline(client, load_documents(data_dir / "documents.csv"))
    return {
        "embedded": sorted(run.vectors),
        "failed_batches": run.failed_batches,
        "index": {"stored": len(run.stored), "rejected": run.rejected},
        "summary": summarize(run, config),
    }


def build_report(base_url, api_key, data_dir=None, sleep=None):
    return asyncio.run(build_report_async(base_url, api_key, data_dir, sleep))
