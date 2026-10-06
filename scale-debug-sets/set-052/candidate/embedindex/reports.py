import asyncio
from pathlib import Path

from .config import load_config
from .indexer import run_index
from .loader import load_documents

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def tally(results, counts={}):
    for r in results:
        counts["docs"] = counts.get("docs", 0) + len(r.doc_ids)
        counts["embedded"] = counts.get("embedded", 0) + len(r.vectors)
    return counts


def summarize(results, usage):
    collections = sorted({r.collection for r in results})
    return {
        "docs": sum(len(r.doc_ids) for r in results),
        "embedded": sum(len(r.vectors) for r in results),
        "by_collection": {c: tally([r for r in results if r.collection == c]) for c in collections},
        "total_tokens": sum(u["total_tokens"] for u in usage),
    }


def build_report(base_url, api_key, data_dir=None, sleep=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    documents = load_documents(data_dir / "documents.csv")
    results, usage = asyncio.run(run_index(base_url, api_key, config, documents, sleep=sleep))
    return {
        "batches": {
            r.batch_id: {"docs": r.doc_ids, "status": r.status, "http_status": r.http_status,
                         "attempts": r.attempts}
            for r in results
        },
        "vectors": {doc_id: vec for r in results for doc_id, vec in r.vectors.items()},
        "summary": summarize(results, usage),
    }
