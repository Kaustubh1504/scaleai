import asyncio
from urllib.parse import urlencode

from .cache import VectorCache
from .loader import unique_texts
from .retry import RETRYABLE, RetryPolicy, send_with_retries
from .transport import request_json


class EmbeddingError(Exception):
    def __init__(self, status):
        super().__init__(f"embedding request failed with HTTP {status}")
        self.status = status


def parse_vectors(body, expected):
    data = (body or {}).get("data") if isinstance(body, dict) else None
    if not isinstance(data, list) or len(data) != expected:
        raise ValueError("response does not hold one embedding per input")
    return [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]


def batched(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]


class EmbeddingClient:
    def __init__(self, base_url, api_key, config, sleep=asyncio.sleep, cache=None):
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.sleep = sleep
        self.cache = cache if cache is not None else VectorCache()
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.policy = RetryPolicy(config.max_retries, config.backoff_seconds)
        self.sem = asyncio.Semaphore(config.max_concurrency)

    async def embed_batch(self, model, texts):
        url = f"{self.base_url}/v1/embeddings"
        payload = {"model": model, "input": texts}
        response = await send_with_retries(
            lambda: request_json("POST", url, self.headers, payload), self.policy, self.sleep)
        if response.status in RETRYABLE:
            raise EmbeddingError(response.status)
        return parse_vectors(response.body, len(texts))

    async def embed_model(self, model, docs):
        """Embed every distinct text for one model. Returns {text: failure dict} for failed texts."""
        pending = [text for text in unique_texts(docs) if (model, text) not in self.cache]
        batches = batched(pending, self.config.batch_size)
        outcomes = await asyncio.gather(*(self.embed_batch(model, b) for b in batches), return_exceptions=True)
        failures = {}
        for batch, outcome in zip(batches, outcomes):
            if isinstance(outcome, EmbeddingError):
                reason = "transient" if outcome.status in RETRYABLE else "rejected"
                failure = {"status": "failed", "http_status": outcome.status, "reason": reason}
            elif isinstance(outcome, Exception):
                failure = {"status": "failed", "http_status": None, "reason": "invalid_response"}
            else:
                for text, vector in zip(batch, outcome):
                    self.cache.put(model, text, vector)
                continue
            failures.update({text: failure for text in batch})
        return failures

    async def usage_page(self, cursor=None):
        query = {"limit": self.config.page_size}
        if cursor:
            query["cursor"] = cursor
        response = await request_json("GET", f"{self.base_url}/v1/usage?{urlencode(query)}", self.headers)
        if response.status != 200:
            raise RuntimeError(f"usage request failed with HTTP {response.status}")
        return response.body
