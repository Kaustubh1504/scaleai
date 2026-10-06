import asyncio
from urllib.parse import urlencode

from .errors import JobFailed, raise_for_status
from .transport import request


class BatchClient:
    def __init__(self, base_url, api_key, config, sleep=asyncio.sleep):
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.sleep = sleep
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.waits = []

    async def pause(self, label, kind, seconds):
        self.waits.append([label, kind, round(seconds, 3)])
        await self.sleep(seconds)

    async def create(self, batch):
        payload = {"model": batch.model, "collection": batch.collection, "inputs": list(batch.inputs)}
        response = await request("POST", f"{self.base_url}/v1/batches", self.headers, payload)
        raise_for_status(response)
        return response.body["id"]

    async def wait_until_done(self, label, batch_id):
        while True:
            response = await request("GET", f"{self.base_url}/v1/batches/{batch_id}", self.headers)
            raise_for_status(response)
            status = response.body["status"]
            if status == "completed":
                return
            if status == "failed":
                raise JobFailed((response.body.get("error") or {}).get("code", "failed"))
            await self.pause(label, "poll", self.config.poll_interval_s)

    async def results(self, batch_id):
        items, token = [], None
        while True:
            query = {"page_size": self.config.page_size}
            if token:
                query["page_token"] = token
            url = f"{self.base_url}/v1/batches/{batch_id}/results?{urlencode(query)}"
            response = await request("GET", url, self.headers)
            raise_for_status(response)
            items.extend(response.body["results"])
            token = response.body.get("next_page_token")
            if not token:
                return items
