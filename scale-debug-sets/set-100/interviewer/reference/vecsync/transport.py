import asyncio
import json
import urllib.error
import urllib.request
from urllib.parse import urlencode


def _decode(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw.decode("utf-8", errors="replace")


# VERIFIED
def request(method, url, headers, payload=None, timeout=5.0):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), _decode(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), _decode(err.read())


class Transport:
    """Async facade over urllib: every call runs in a worker thread."""

    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def get(self, path, params=None):
        url = f"{self.base_url}{path}" + (f"?{urlencode(params)}" if params else "")
        return await asyncio.to_thread(request, "GET", url, self.headers)

    async def post(self, path, payload):
        return await asyncio.to_thread(request, "POST", f"{self.base_url}{path}", self.headers, payload)

    async def delete(self, path):
        return await asyncio.to_thread(request, "DELETE", f"{self.base_url}{path}", self.headers)
