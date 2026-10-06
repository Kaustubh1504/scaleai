import asyncio

from .client import EmbeddingClient
from .config import load_config
from .corpus import load_corpus, make_batches
from .index import list_index_ids


async def run(base_url, api_key, config=None, corpus_path=None):
    config = config or load_config()
    docs = load_corpus(corpus_path)
    batches = make_batches(docs, config.batch_size)
    client = EmbeddingClient(base_url, api_key, config)
    vectors, failed = await client.embed_all(batches)
    index_ids = await list_index_ids(base_url, client.headers, config.index_page_size)
    corpus_ids = {doc_id for doc_id, _ in docs}
    missing = sorted(doc_id for doc_id, _ in docs if doc_id not in vectors)
    return {
        "batches": {b.id: list(b.doc_ids) for b in batches},
        "vectors": dict(sorted(vectors.items())),
        "failed": dict(sorted(failed.items())),
        "summary": {
            "embedded": len(vectors),
            "missing_docs": missing,
            "total_tokens": client.usage_tokens,
            "stale_ids": sorted(set(index_ids) - corpus_ids),
        },
    }


def build_report(base_url, api_key, **kwargs):
    return asyncio.run(run(base_url, api_key, **kwargs))
