import asyncio
import math

from .models import EmbeddingError
from .retry import RetryPolicy, send_with_retries


# VERIFIED
def parse_vectors(body, batch):
    """Map the response rows back to doc ids by their `index`, not their position."""
    vectors = {}
    for row in body["data"]:
        vectors[batch.doc_ids[row["index"]]] = row["embedding"]
    return vectors


def summarize_vector(vector):
    return {"dims": len(vector), "norm": round(math.sqrt(sum(x * x for x in vector)), 3)}


class Embedder:
    def __init__(self, transport, config, sleep=asyncio.sleep):
        self.transport = transport
        self.config = config
        self.sleep = sleep
        self.policy = RetryPolicy(config.max_retries, config.backoff_seconds)
        self.limit = asyncio.Semaphore(config.max_concurrency)
        self.attempts = {}

    def payload(self, batch):
        return {
            "model": self.config.model,
            "input": [d.text for d in batch.docs],
            "metadata": {"batch_id": batch.id},
        }

    def _record(self, batch_id, attempt):
        self.attempts[batch_id] = attempt

    async def embed_batch(self, batch):
        batch_id = batch.id
        async with self.limit:
            status, _, body = await send_with_retries(
                lambda: self.transport.post("/v1/embeddings", self.payload(batch)),
                self.policy,
                self.sleep,
                on_attempt=lambda n: self._record(batch_id, n),
            )
        if status != 200:
            raise EmbeddingError(f"HTTP {status}")
        return parse_vectors(body, batch)

    async def embed_all(self, batches):
        outcomes = await asyncio.gather(*(self.embed_batch(b) for b in batches), return_exceptions=True)
        embedded, failed = {}, {}
        for batch, outcome in zip(batches, outcomes):
            if isinstance(outcome, BaseException):
                failed[batch.id] = str(outcome)
            else:
                embedded.update(outcome)
        return embedded, failed
