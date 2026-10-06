import asyncio
from dataclasses import dataclass, field

from .client import EmbeddingError
from .loader import batched


@dataclass
class RunResult:
    docs: list
    vectors: dict = field(default_factory=dict)
    failed_batches: list = field(default_factory=list)
    total_tokens: int = 0
    stored: dict = field(default_factory=dict)
    rejected: list = field(default_factory=list)


async def embed_documents(client, docs, run):
    batches = batched(docs, client.config.batch_size)
    outcomes = await asyncio.gather(
        *(client.embed_batch(i, [d.text for d in batch]) for i, batch in enumerate(batches)),
        return_exceptions=True,
    )
    for i, (batch, outcome) in enumerate(zip(batches, outcomes)):
        if isinstance(outcome, EmbeddingError):
            run.failed_batches.append({"batch": i, "status": outcome.status,
                                       "doc_ids": [d.doc_id for d in batch]})
            continue
        if isinstance(outcome, BaseException):
            raise outcome
        vectors, tokens = outcome
        run.total_tokens += tokens
        for doc, vector in zip(batch, vectors):
            run.vectors[doc.doc_id] = vector


async def index_vectors(client, run):
    doc_ids = sorted(run.vectors)
    results = await asyncio.gather(
        *(client.upsert(doc_id, run.vectors[doc_id]) for doc_id in doc_ids),
        return_exceptions=True,
    )
    for doc_id, result in zip(doc_ids, results):
        if isinstance(result, Exception):
            run.rejected.append(doc_id)
        else:
            run.stored[doc_id] = result


async def run_pipeline(client, docs):
    run = RunResult(docs=docs)
    await embed_documents(client, docs, run)
    await index_vectors(client, run)
    return run
