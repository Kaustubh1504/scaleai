import asyncio
from dataclasses import dataclass, field
from urllib.parse import urlencode

from .parsing import DimensionMismatch, ResponseError, parse_embeddings, usage_tokens
from .retry import with_retries
from .transport import request


class UpsertError(Exception):
    def __init__(self, batch_id, status):
        super().__init__(f"upsert of {batch_id} failed with HTTP {status}")
        self.batch_id = batch_id


@dataclass
class BatchResult:
    batch_id: str
    status: str
    record_ids: list
    http_status: int | None = None
    attempts: int = 0
    tokens: int = 0
    vectors: list = field(default_factory=list)


class EmbeddingClient:
    def __init__(self, base_url, api_key, config):
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.sem = asyncio.Semaphore(config.max_concurrency)

    async def records_page(self, token=None):
        query = {"limit": self.config.page_size}
        if token:
            query["page_token"] = token
        url = f"{self.base_url}/v1/datasets/{self.config.dataset}/records?{urlencode(query)}"
        response = await request("GET", url, self.headers)
        if response.status != 200:
            raise RuntimeError(f"records page failed with HTTP {response.status}")
        return response.body

    def _payload(self, batch_id, records):
        return {
            "model": self.config.model,
            "input": [r["text"] for r in records],
            "dimensions": self.config.dimensions,
            "metadata": {"batch_id": batch_id},
        }

    async def _send_embeddings(self, batch_id, records):
        payload = self._payload(batch_id, records)
        url = f"{self.base_url}/v1/embeddings"
        return await with_retries(lambda: request("POST", url, self.headers, payload),
                                  self.config.max_retries, self.config.backoff_s)

    async def embed_batch(self, batch_id, records):
        ids = [r["id"] for r in records]
        response, attempts = await self._send_embeddings(batch_id, records)
        result = BatchResult(batch_id, "ok", ids, http_status=response.status, attempts=attempts)
        if response.status >= 500:
            result.status = "http_error"
            return result
        try:
            result.vectors = parse_embeddings(response.body, len(records), self.config.dimensions)
        except ResponseError:
            result.status = "bad_response"
        except DimensionMismatch:
            result.status = "dim_mismatch"
        else:
            result.tokens = usage_tokens(response.body)
        return result

    async def upsert(self, result):
        payload = {"batch_id": result.batch_id,
                   "items": [{"id": i, "vector": v} for i, v in zip(result.record_ids, result.vectors)]}
        async with self.sem:
            response = await request("POST", f"{self.base_url}/v1/index/upsert", self.headers, payload)
        if response.status != 200:
            raise UpsertError(result.batch_id, response.status)
        return result.batch_id
