import asyncio
import math

from .payloads import build_body, encode_body
from .retry import send_with_retries
from .transport import post


class EmbeddingClient:
    def __init__(self, base_url, api_key, config):
        self.url = base_url.rstrip("/") + "/v1/embeddings"
        self.config = config
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self._limit = asyncio.Semaphore(config.max_concurrency)

    async def embed_batch(self, batch):
        data = encode_body(build_body(self.config.model, batch))
        async with self._limit:
            response, attempts = await send_with_retries(
                lambda: post(self.url, data, self.headers, self.config.timeout_s),
                self.config.max_retries, self.config.backoff_s,
            )
        return self._outcome(batch, response, attempts)

    def _outcome(self, batch, response, attempts):
        outcome = {"batch_id": batch["batch_id"], "attempts": attempts, "http_status": response.status,
                   "doc_ids": [d["doc_id"] for d in batch["docs"]], "tokens": 0, "vectors": {}}
        if response.status != 200:
            outcome["status"] = "failed"
            return outcome
        outcome["status"] = "ok"
        outcome["tokens"] = response.body["usage"]["total_tokens"]
        for item in response.body["data"]:
            doc = batch["docs"][item["index"]]
            outcome["vectors"][doc["doc_id"]] = item["embedding"]
        return outcome

    async def embed_all(self, batches):
        return await asyncio.gather(*(self.embed_batch(b) for b in batches))


def vector_norm(vector):
    return round(math.sqrt(sum(x * x for x in vector)), 3)
