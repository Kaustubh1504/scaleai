import asyncio

from .retry import RetryPolicy, with_retries
from .transport import send


class BatchError(Exception):
    def __init__(self, batch, status):
        super().__init__(f"batch {batch.batch_id} failed with HTTP {status}")
        self.batch = batch
        self.status = status


class EmbeddingClient:
    def __init__(self, base_url, api_key, config, sleep=asyncio.sleep):
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.sleep = sleep
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.policy = RetryPolicy(config.max_retries, config.backoff_seconds)
        self._limit = None

    def build_request(self, batch):
        return {
            "model": self.config.model,
            "dimensions": self.config.dimensions,
            "input": [doc.text for doc in batch.docs],
            "documents": [{"id": doc.doc_id, "updated_at": doc.updated_at} for doc in batch.docs],
            "metadata": {"batch_id": batch.batch_id},
        }

    async def embed_batch(self, batch):
        payload = self.build_request(batch)
        url = f"{self.base_url}/v1/embeddings"
        response = await with_retries(lambda: send("POST", url, self.headers, payload), self.policy, self.sleep)
        if response.status != 200:
            raise BatchError(batch, response.status)
        vectors = {}
        for item in response.body["data"]:
            vectors[batch.docs[item["index"]].doc_id] = item["embedding"]
        return vectors, response.body["usage"]["total_tokens"]

    async def _bounded(self, batch):
        async with self._limit:
            return await self.embed_batch(batch)

    async def embed_all(self, batches):
        self._limit = asyncio.Semaphore(self.config.max_concurrency)
        return await asyncio.gather(*(self._bounded(b) for b in batches), return_exceptions=True)
