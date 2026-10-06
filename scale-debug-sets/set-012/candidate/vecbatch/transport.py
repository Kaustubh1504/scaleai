import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass
class Response:
    status: int
    headers: dict = field(default_factory=dict)
    text: str = ""

    def json(self):
        return json.loads(self.text)


# VERIFIED
def _send(method, url, headers, payload, timeout):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return Response(resp.status, dict(resp.headers), resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return Response(err.code, dict(err.headers), err.read().decode("utf-8", errors="replace"))


async def request(method, url, headers, payload=None, timeout=5.0):
    return await asyncio.to_thread(_send, method, url, dict(headers), payload, timeout)
