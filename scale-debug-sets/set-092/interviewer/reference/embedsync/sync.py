from dataclasses import dataclass, field

from .client import BatchError, EmbeddingClient
from .documents import make_batches
from .index import list_index


@dataclass
class SyncResult:
    outcomes: dict = field(default_factory=dict)
    embeddings: dict = field(default_factory=dict)
    to_delete: list = field(default_factory=list)
    errors: dict = field(default_factory=dict)
    total_tokens: int = 0


async def run_sync(base_url, api_key, config, docs, retired, sleep=None):
    kwargs = {"sleep": sleep} if sleep else {}
    client = EmbeddingClient(base_url, api_key, config, **kwargs)
    active = {doc_id: doc for doc_id, doc in docs.items() if doc_id not in retired}
    result = SyncResult()

    pending = []
    for collection in sorted({doc.collection for doc in docs.values()}):
        indexed = {item["doc_id"]: item["sha1"]
                   for item in await list_index(client.base_url, client.headers, collection, config.page_size)}
        members = [doc for doc in active.values() if doc.collection == collection]
        for doc in members:
            if indexed.get(doc.doc_id) == doc.sha1:
                result.outcomes[doc.doc_id] = "skipped"
            else:
                pending.append(doc)
        result.to_delete.extend(doc_id for doc_id in indexed if doc_id not in active)

    batches = make_batches(pending, config.batch_size)
    outcomes = await client.embed_all(batches)
    for batch, outcome in zip(batches, outcomes):
        if isinstance(outcome, BatchError):
            result.errors[batch.batch_id] = outcome.status
            for doc in batch.docs:
                result.outcomes[doc.doc_id] = "failed"
            continue
        if isinstance(outcome, BaseException):
            raise outcome
        vectors, tokens = outcome
        result.embeddings.update(vectors)
        result.total_tokens += tokens
        for doc_id in vectors:
            result.outcomes[doc_id] = "embedded"
    result.to_delete.sort()
    return result
