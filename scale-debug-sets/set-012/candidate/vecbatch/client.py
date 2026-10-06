import asyncio
import json
from dataclasses import dataclass, field
from urllib.parse import urlencode

from .parsing import parse_embeddings
from .retry import send_with_retries
from .transport import request


@dataclass
class Batch:
    batch_id: str
    doc_ids: list
    texts: list


@dataclass
class BatchResult:
    batch_id: str
    status: str
    attempts: int
    http_status: int | None = None
    vectors: list = field(default_factory=list)


class EmbeddingClient:
    def __init__(self, base_url, api_key, config):
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.semaphore = asyncio.Semaphore(config.max_concurrency)

    def build_request(self, batch):
        return {
            "model": self.config.model,
            "input": batch.texts,
            "dimensions": self.config.dimensions,
            "metadata": {"batch_id": batch.batch_id},
        }

    async def _post(self, payload):
        return await request("POST", f"{self.base_url}/v1/embeddings", self.headers, payload)

    async def embed_batch(self, batch):
        payload = self.build_request(batch)
        response, attempts = await send_with_retries(
            lambda: self._post(payload), self.config.max_retries, self.config.backoff_seconds)
        if response.status >= 400:
            return BatchResult(batch.batch_id, "http_error", attempts, http_status=response.status)
        try:
            vectors = parse_embeddings(response.text, len(batch.texts), self.config.dimensions)
        except ValueError:
            return BatchResult(batch.batch_id, "invalid", attempts, http_status=response.status)
        except json.JSONDecodeError:
            return BatchResult(batch.batch_id, "bad_json", attempts, http_status=response.status)
        return BatchResult(batch.batch_id, "embedded", attempts, http_status=response.status, vectors=vectors)

    async def usage_page(self, after=None):
        query = {"limit": self.config.usage_page_size}
        if after:
            query["after"] = after
        response = await request("GET", f"{self.base_url}/v1/usage?{urlencode(query)}", self.headers)
        if response.status != 200:
            raise RuntimeError(f"usage request failed with HTTP {response.status}")
        return response.json()
