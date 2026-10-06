import asyncio
from urllib.parse import quote, urlencode

from .models import BatchResult, BatchStatus
from .retry import send_with_retries
from .transport import send


def interpret(batch, response, dimensions):
    if response.status != 200:
        return BatchResult(batch.batch_id, batch.collection, batch.doc_ids, BatchStatus.FAILED, response.status)
    vectors = (response.body or {}).get("data") or []
    well_formed = len(vectors) == len(batch.documents) and all(
        len(v.get("embedding") or []) == dimensions for v in vectors
    )
    status = BatchStatus.OK if well_formed else BatchStatus.REJECTED
    return BatchResult(batch.batch_id, batch.collection, batch.doc_ids, status, response.status)


class EmbeddingClient:
    def __init__(self, base_url, api_key, config, sleep=None):
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.sleep = sleep or asyncio.sleep
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self._slots = asyncio.Semaphore(config.max_concurrency)

    def build_payload(self, batch, dimensions):
        return {
            "model": self.config.model,
            "collection": batch.collection,
            "batch_id": batch.batch_id,
            "dimensions": dimensions,
            "input": [{"id": d.doc_id, "text": d.text} for d in batch.documents],
        }

    async def embed_batch(self, batch, dimensions):
        payload = self.build_payload(batch, dimensions)
        url = f"{self.base_url}/v1/embeddings"
        async with asyncio.Semaphore(self.config.max_concurrency):
            response = await send_with_retries(
                lambda: send("POST", url, self.headers, payload),
                self.config.max_retries, self.config.backoff_seconds, self.sleep,
            )
        return interpret(batch, response, dimensions)

    async def commit(self, accepted, documents):
        url = f"{self.base_url}/v1/jobs/{quote(self.config.job_id)}/commit"
        return await send("POST", url, self.headers, {"accepted": accepted, "documents": documents})

    async def vector_page(self, collection, offset):
        query = urlencode({"offset": offset, "limit": self.config.page_size})
        url = f"{self.base_url}/v1/collections/{quote(collection)}/vectors?{query}"
        response = await send("GET", url, self.headers)
        if response.status != 200:
            raise RuntimeError(f"listing {collection} failed with HTTP {response.status}")
        return response.body
