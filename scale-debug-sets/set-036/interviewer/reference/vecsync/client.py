import asyncio

from .retry import RetryPolicy, send_with_retries
from .transport import send


class EmbeddingError(Exception):
    def __init__(self, batch, status):
        super().__init__(f"batch {batch} failed with HTTP {status}")
        self.batch = batch
        self.status = status


class UpsertError(Exception):
    pass


class EmbeddingClient:
    def __init__(self, base_url, api_key, config, sleep=asyncio.sleep):
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.sleep = sleep
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.policy = RetryPolicy(config.max_retries, config.backoff_seconds)
        self.limit = asyncio.Semaphore(config.max_concurrency)

    async def _call(self, method, path, payload=None):
        return await asyncio.to_thread(send, method, self.base_url + path, self.headers, payload)

    async def embed_batch(self, index, texts):
        """Return (vectors in input order, prompt_tokens) or raise EmbeddingError."""
        payload = {"model": self.config.model, "input": texts, "metadata": {"batch": index}}
        async with self.limit:
            response = await send_with_retries(
                lambda: self._call("POST", "/v1/embeddings", payload), self.policy, self.sleep)
        if response.status >= 400:
            raise EmbeddingError(index, response.status)
        items = sorted(response.body["data"], key=lambda item: item["index"])
        return [item["embedding"] for item in items], response.body["usage"]["prompt_tokens"]

    async def upsert(self, doc_id, vector):
        """Store one vector in the index; returns the stored version number."""
        payload = {"model": self.config.model, "embedding": vector}
        async with self.limit:
            response = await self._call("PUT", f"/v1/index/{doc_id}", payload)
        if response.status != 200:
            raise UpsertError(f"{doc_id}: HTTP {response.status}")
        return response.body["version"]
