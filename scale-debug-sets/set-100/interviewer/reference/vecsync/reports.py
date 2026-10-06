import asyncio
from pathlib import Path

from .config import load_config
from .embedder import Embedder, summarize_vector
from .index import list_index, remove_stale
from .loader import load_documents, make_batches
from .transport import Transport

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


async def sync_index(base_url, api_key, data_dir, sleep):
    config = load_config(data_dir / "config.json")
    transport = Transport(base_url, api_key)
    docs = load_documents(data_dir / "documents.csv")
    batches = make_batches(docs, config.batch_size)
    embedder = Embedder(transport, config, **({"sleep": sleep} if sleep else {}))
    embedded, failed = await embedder.embed_all(batches)
    current = {d.id for d in docs}
    stale = sorted(i for i in await list_index(transport, config.index_page_size) if i not in current)
    deleted, delete_failed = await remove_stale(transport, stale)
    return {
        "batches": {b.id: b.doc_ids for b in batches},
        "embedded": {doc_id: summarize_vector(v) for doc_id, v in sorted(embedded.items())},
        "failed_batches": dict(sorted(failed.items())),
        "attempts": dict(sorted(embedder.attempts.items())),
        "stale": stale,
        "deleted": deleted,
        "delete_failed": delete_failed,
    }


def build_report(base_url, api_key, data_dir=None, sleep=None):
    return asyncio.run(sync_index(base_url, api_key, Path(data_dir or DATA_DIR), sleep))
