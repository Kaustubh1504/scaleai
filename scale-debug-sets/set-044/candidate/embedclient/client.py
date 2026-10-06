import asyncio

from .retry import post_with_retries


class BatchFailed(Exception):
    pass


class EmbeddingClient:
    def __init__(self, base_url, api_key, config):
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.usage_tokens = 0
        self._sem = asyncio.Semaphore(config.max_concurrency)

    def build_payload(self, batch):
        return {"model": self.config.model, "input": list(batch.texts), "metadata": {"batch": batch.id}}

    async def _embed_batch(self, batch):
        payload = self.build_payload(batch)
        tokens_before = self.usage_tokens
        resp = await post_with_retries(f"{self.base_url}/v1/embeddings", self.headers, payload,
                                       self.config.max_retries, self.config.backoff_seconds)
        if resp.status != 200:
            raise BatchFailed(f"HTTP {resp.status}")
        body = resp.body
        self.usage_tokens = tokens_before + body["usage"]["total_tokens"]
        return {batch.doc_ids[item["index"]]: item["embedding"] for item in body["data"]}

    async def _run_batch(self, batch):
        async with asyncio.Semaphore(self.config.max_concurrency):
            return await self._embed_batch(batch)

    async def embed_all(self, batches):
        results = await asyncio.gather(*(self._run_batch(b) for b in batches), return_exceptions=True)
        vectors, failed = {}, {}
        for batch, result in zip(batches, results):
            if isinstance(result, Exception):
                continue
            vectors.update(result)
        return vectors, failed
