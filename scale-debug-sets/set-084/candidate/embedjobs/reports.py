import asyncio
import math
from pathlib import Path

from .client import BatchClient
from .config import load_config
from .documents import load_collections, load_documents, make_batches
from .runner import run_batches

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def l2_norm(vector):
    return round(math.sqrt(sum(x * x for x in vector)), 4)


def build_report(base_url, api_key, data_dir=None, sleep=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    collections = load_collections(data_dir / "collections.json", config.model)
    docs, skipped = load_documents(data_dir / "documents.csv", collections)
    batches = make_batches(docs, collections, config.batch_size)
    client = BatchClient(base_url, api_key, config, **({"sleep": sleep} if sleep else {}))
    embedded, failures = asyncio.run(run_batches(client, batches))
    return {
        "batches": [b.label for b in batches],
        "embedded": {doc_id: {"dims": len(vec), "norm": l2_norm(vec)} for doc_id, vec in sorted(embedded.items())},
        "failures": dict(sorted(failures.items())),
        "skipped": skipped,
        "waits": client.waits,
    }
