"""Minimal HTTP/1.1 over asyncio streams: one request per connection."""
import asyncio
import json
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit


class EvalError(Exception):
    pass


@dataclass
class Response:
    status: int
    headers: dict
    body: bytes

    def json(self):
        return json.loads(self.body) if self.body else None


def _encode_request(method, target, host, headers, body):
    lines = [f"{method} {target} HTTP/1.1", f"Host: {host}", "Connection: close"]
    lines += [f"{name}: {value}" for name, value in headers.items()]
    lines.append(f"Content-Length: {len(body)}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + body


async def _read_head(reader):
    status_line = await reader.readline()
    status = int(status_line.split()[1])
    headers = {}
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            return status, headers
        name, _, value = line.decode("latin-1").partition(":")
        headers[name.strip().lower()] = value.strip()


# VERIFIED
async def _read_chunked(reader):
    body = bytearray()
    while True:
        size_line = await reader.readline()
        size = int(size_line.split(b";")[0].strip() or b"0", 16)
        if size == 0:
            await reader.readline()
            return bytes(body)
        chunk = await reader.readexactly(size + 2)
        body += chunk[:-2]


async def send(base_url, method, path, headers, payload=None, params=None):
    parts = urlsplit(base_url)
    target = path + (f"?{urlencode(params)}" if params else "")
    body = json.dumps(payload).encode() if payload is not None else b""
    reader, writer = await asyncio.open_connection(parts.hostname, parts.port)
    try:
        writer.write(_encode_request(method, target, parts.netloc, headers, body))
        await writer.drain()
        status, head = await _read_head(reader)
        if head.get("transfer-encoding", "").lower() == "chunked":
            data = await _read_chunked(reader)
        elif "content-length" in head:
            data = await reader.readexactly(int(head["content-length"]))
        else:
            data = await reader.read()
        return Response(status, head, data)
    finally:
        writer.close()
        await writer.wait_closed()
