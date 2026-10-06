import asyncio
import math
from dataclasses import dataclass, field
from urllib.parse import urlencode

from .retry import RetryPolicy, send_with_retries
from .transport import send


@dataclass
class BatchResult:
    batch_id: str
    collection: str
    doc_ids: list
    status: str
    http_status: int
    attempts: int
    vectors: dict = field(default_factory=dict)


def l2_normalize(vector):
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return list(vector)
    return [x / norm for x in vector]


def parse_vectors(body):
    """Embeddings from a response body, ordered by their `index` field."""
    data = (body or {}).get("data", []) if isinstance(body, dict) else []
    return [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]


class EmbeddingClient:
    def __init__(self, base_url, api_key, config, sleep=asyncio.sleep):
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.sleep = sleep
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.policy = RetryPolicy(config.max_retries, config.backoff_seconds)
        self.defaults = dict(config.defaults)
        self.limit = asyncio.Semaphore(config.max_concurrency)

    async def _call(self, method, path, payload=None):
        return await asyncio.to_thread(send, method, self.base_url + path, self.headers, payload)

    def build_payload(self, batch):
        return {
            "model": self.config.model,
            "input": [doc.text for doc in batch.docs],
            "dimensions": self.config.dimensions,
            "user": batch.batch_id,
        }

    async def embed_batch(self, batch):
        options = dict(self.defaults)
        options.update(self.config.options_for(batch.collection))
        payload = self.build_payload(batch)
        async with self.limit:
            response, attempts = await send_with_retries(
                lambda: self._call("POST", "/v1/embeddings", payload), self.policy, self.sleep)
        doc_ids = [doc.doc_id for doc in batch.docs]
        result = BatchResult(batch.batch_id, batch.collection, doc_ids, "ok", response.status, attempts)
        if response.status != 200:
            result.status = "failed"
            return result
        for doc_id, vector in zip(doc_ids, parse_vectors(response.body)):
            if options.get("normalize"):
                vector = l2_normalize(vector)
            result.vectors[doc_id] = [round(x, 4) for x in vector]
        return result

    async def usage_page(self, cursor=None):
        query = {"limit": self.config.usage_page_size}
        if cursor:
            query["cursor"] = cursor
        response = await self._call("GET", f"/v1/usage?{urlencode(query)}")
        if response.status != 200:
            raise RuntimeError(f"usage request failed with HTTP {response.status}")
        return response.body
