import asyncio
from dataclasses import dataclass
from itertools import groupby

from .client import EmbeddingClient


@dataclass
class Batch:
    batch_id: str
    collection: str
    docs: list


# VERIFIED
def make_batches(documents, size):
    """Per collection (alphabetical), documents in file order, `size` at a time."""
    batches = []
    ordered = sorted(documents, key=lambda d: d.collection)
    for collection, group in groupby(ordered, key=lambda d: d.collection):
        docs = list(group)
        for n, start in enumerate(range(0, len(docs), size), start=1):
            batches.append(Batch(f"{collection}-{n:02d}", collection, docs[start:start + size]))
    return batches


async def fetch_usage(client):
    page = await client.usage_page()
    records = list(page["data"])
    while page.get("next_cursor"):
        page = await client.usage_page(page["next_cursor"])
        records.extend(page["data"])
    return records


async def run_index(base_url, api_key, config, documents, sleep=None):
    client = EmbeddingClient(base_url, api_key, config, sleep=sleep or asyncio.sleep)
    batches = make_batches(documents, config.batch_size)
    results = await asyncio.gather(*(client.embed_batch(b) for b in batches))
    usage = await fetch_usage(client)
    return list(results), usage
