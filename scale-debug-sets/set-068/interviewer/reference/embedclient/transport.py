import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass
class Response:
    status: int
    headers: dict = field(default_factory=dict)
    body: object = None


def _decode(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw.decode("utf-8", errors="replace")


# VERIFIED
def send_sync(url, data, headers, timeout):
    request = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return Response(resp.status, dict(resp.headers), _decode(resp.read()))
    except urllib.error.HTTPError as err:
        return Response(err.code, dict(err.headers), _decode(err.read()))


async def post(url, data, headers, timeout):
    """Run the blocking urllib call in a worker thread so batches can overlap."""
    return await asyncio.to_thread(send_sync, url, data, headers, timeout)
