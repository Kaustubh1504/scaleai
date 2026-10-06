import asyncio
from pathlib import Path

from .pipeline import run
from .similarity import near_duplicates

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(base_url, api_key, data_dir=None):
    config, batches, results, usage = asyncio.run(run(base_url, api_key, data_dir or DATA_DIR))
    documents, vectors = {}, {}
    for batch, result in zip(batches, results):
        for i, doc_id in enumerate(batch.doc_ids):
            documents[doc_id] = result.status
            if result.status == "embedded":
                vectors[doc_id] = result.vectors[i]
    embedded = sum(1 for s in documents.values() if s == "embedded")
    return {
        "batches": {r.batch_id: {"status": r.status, "attempts": r.attempts} for r in results},
        "documents": documents,
        "counts": {"embedded": embedded, "failed": len(documents) - embedded},
        "total_tokens": sum(u["total_tokens"] for u in usage),
        "near_duplicates": near_duplicates(vectors, config.duplicate_threshold),
    }
