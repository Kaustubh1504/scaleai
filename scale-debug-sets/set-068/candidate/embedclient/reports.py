import asyncio
from collections import Counter
from pathlib import Path

from .client import EmbeddingClient, vector_norm
from .config import load_config
from .payloads import load_documents, make_batches

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


async def run_backfill(base_url, api_key, data_dir):
    config = load_config(data_dir / "config.json")
    docs = load_documents(data_dir / "documents.csv")
    batches = make_batches(docs, config.batch_size)
    client = EmbeddingClient(base_url, api_key, config)
    return docs, await client.embed_all(batches)


def summarize(docs, outcomes):
    collection = {d["doc_id"]: d["collection"] for d in docs}
    embedded = [doc_id for o in outcomes for doc_id in o["vectors"]]
    failed = [doc_id for o in outcomes if o["status"] == "failed" for doc_id in o["doc_ids"]]
    total_tokens = sum(o["tokens"] for o in outcomes)
    by_collection = Counter(collection[doc_id] for doc_id in embedded)
    return {
        "embedded": len(embedded),
        "failed": len(failed),
        "total_tokens": total_tokens,
        "tokens_per_doc": round(total_tokens // len(embedded), 2) if embedded else None,
        "by_collection": dict(sorted(by_collection.items())),
    }


def build_report(base_url, api_key, data_dir=None):
    docs, outcomes = asyncio.run(run_backfill(base_url, api_key, Path(data_dir or DATA_DIR)))
    results = {}
    for o in outcomes:
        for doc_id in o["doc_ids"]:
            if doc_id in o["vectors"]:
                results[doc_id] = {"status": "ok", "norm": vector_norm(o["vectors"][doc_id])}
            else:
                results[doc_id] = {"status": "failed", "http_status": o["http_status"]}
    return {
        "batches": {o["batch_id"]: {"doc_ids": o["doc_ids"], "status": o["status"],
                                     "http_status": o["http_status"], "attempts": o["attempts"]}
                    for o in outcomes},
        "docs": results,
        "summary": summarize(docs, outcomes),
    }
