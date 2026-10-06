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


def _blocking(method, url, headers, payload, timeout):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return Response(resp.status, dict(resp.headers), _decode(resp.read()))
    except urllib.error.HTTPError as err:
        return Response(err.code, dict(err.headers), _decode(err.read()))


async def request(method, url, headers, payload=None, timeout=5.0):
    return await asyncio.to_thread(_blocking, method, url, headers, payload, timeout)
