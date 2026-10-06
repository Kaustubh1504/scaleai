import asyncio
import csv
from pathlib import Path

from .client import Batch, EmbeddingClient
from .config import load_config


def load_documents(path):
    docs = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            text = (row["text"] or "").strip()
            status = (row["status"] or "").strip().lower()
            if not text or status == "archived":
                continue
            docs.append((row["doc_id"].strip().lower(), text))
    return docs


# VERIFIED
def make_batches(docs, size):
    batches = []
    for n, start in enumerate(range(0, len(docs), size), start=1):
        chunk = docs[start:start + size]
        batches.append(Batch(f"b{n:02d}", [d for d, _ in chunk], [t for _, t in chunk]))
    return batches


async def collect_usage(client):
    records, after = [], None
    while True:
        page = await client.usage_page(after)
        records.extend(page["data"])
        if not page["has_more"]:
            return records
        after = page["first_id"]


async def run(base_url, api_key, data_dir):
    data_dir = Path(data_dir)
    config = load_config(data_dir / "config.json")
    client = EmbeddingClient(base_url, api_key, config)
    batches = make_batches(load_documents(data_dir / "documents.csv"), config.batch_size)
    results = await asyncio.gather(*(client.embed_batch(b) for b in batches))
    usage = await collect_usage(client)
    return config, batches, list(results), usage
