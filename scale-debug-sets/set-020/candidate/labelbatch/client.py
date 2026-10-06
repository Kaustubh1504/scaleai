import asyncio
from urllib.parse import urlencode

from .transport import send

RETRYABLE = {429, 500, 502, 503, 504}
TERMINAL = {"completed", "failed"}


class BatchError(Exception):
    pass


# VERIFIED
def poll_delay(attempt, interval):
    return interval if attempt else 0.0


class BatchClient:
    def __init__(self, base_url, api_key, config):
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def submit(self, shard, inputs):
        payload = {"model": self.config.model, "shard": shard, "inputs": inputs}
        response = None
        for _ in range(self.config.max_retries + 1):
            response = await send("POST", f"{self.base_url}/v1/batches", self.headers, payload)
            if response.status not in RETRYABLE:
                break
            await asyncio.sleep(float(response.headers.get("Retry-After", 0)))
        if response.status != 201:
            raise BatchError(f"submit for {shard} failed with HTTP {response.status}")
        return response.body["id"]

    async def poll_until_done(self, batch_id):
        for attempt in range(self.config.max_polls):
            await asyncio.sleep(poll_delay(attempt, self.config.poll_interval_s))
            response = await send("GET", f"{self.base_url}/v1/batches/{batch_id}", self.headers)
            if response.status != 200:
                raise BatchError(f"status for {batch_id} failed with HTTP {response.status}")
            if response.body["status"] in TERMINAL:
                return response.body
        return {"id": batch_id, "status": "timeout"}

    async def results_page(self, batch_id, page):
        query = urlencode({"page": page, "limit": self.config.page_size})
        response = await send("GET", f"{self.base_url}/v1/batches/{batch_id}/results?{query}", self.headers)
        if response.status != 200:
            raise BatchError(f"results for {batch_id} failed with HTTP {response.status}")
        return response.body

    async def fetch_results(self, batch_id):
        first = await self.results_page(batch_id, 1)
        items = list(first["data"])
        for page in range(2, first["total_pages"]):
            items.extend((await self.results_page(batch_id, page))["data"])
        return items

    async def archive(self, batch_id):
        await send("DELETE", f"{self.base_url}/v1/batches/{batch_id}", self.headers)
