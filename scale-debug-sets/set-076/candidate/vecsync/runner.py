import asyncio
from dataclasses import dataclass
from pathlib import Path

from .client import EmbeddingClient
from .index import collect_index
from .loader import load_collections, load_config, load_documents, make_batches
from .models import BatchStatus


@dataclass
class JobOutcome:
    results: list
    skipped: list
    index: dict


async def run_job(base_url, api_key, data_dir, sleep=None):
    data_dir = Path(data_dir)
    config = load_config(data_dir / "config.json")
    collections = [c for c in load_collections(data_dir / "collections.json") if c.enabled]
    documents, skipped = load_documents(data_dir / "documents.csv", collections)
    batches = make_batches(documents, collections, config.batch_size)
    dimensions = {c.name: c.dimensions for c in collections}

    client = EmbeddingClient(base_url, api_key, config, sleep=sleep)
    results = await asyncio.gather(*(client.embed_batch(b, dimensions[b.collection]) for b in batches))

    ok = [r for r in results if r.status is BatchStatus.OK]
    accepted = sorted(r.batch_id for r in ok)
    documents_ok = sum(len(r.doc_ids) for r in ok)
    client.commit(accepted, documents_ok)

    index = {}
    for name in dict.fromkeys(b.collection for b in batches):
        index[name] = await collect_index(client, name)
    return JobOutcome(list(results), skipped, index)


def run(base_url, api_key, data_dir, sleep=None):
    return asyncio.run(run_job(base_url, api_key, data_dir, sleep=sleep))
