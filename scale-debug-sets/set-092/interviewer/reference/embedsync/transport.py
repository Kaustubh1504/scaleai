import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class Response:
    status: int
    headers: dict = field(default_factory=dict)
    body: object = None


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"cannot encode {type(value).__name__}")


def encode_body(payload):
    return json.dumps(payload, default=_json_default).encode("utf-8")


# VERIFIED
def _send_sync(method, url, headers, data, timeout):
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw, status, hdrs = resp.read(), resp.status, dict(resp.headers)
    except urllib.error.HTTPError as err:
        raw, status, hdrs = err.read(), err.code, dict(err.headers)
    try:
        body = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        body = raw.decode("utf-8", errors="replace")
    return Response(status, hdrs, body)


async def send(method, url, headers, payload=None, timeout=5.0):
    data = encode_body(payload) if payload is not None else None
    return await asyncio.to_thread(_send_sync, method, url, headers, data, timeout)
