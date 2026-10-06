"""Scripted stand-in for the embeddings service. Test infrastructure: do not modify."""
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

API_KEY = "sk-test-embed"
SERVICE_TIME_S = 0.08


def _ok():
    return (200, None, {})


# batch_id -> responses served in order (the last one repeats). A None payload means
# "embed the inputs normally"; a str payload is sent as the raw body.
SCRIPT = {
    "b01": [_ok()],
    "b02": [(429, {"error": {"message": "rate limited"}}, {"Retry-After": "1"}), _ok()],
    "b03": [(500, {"error": {"message": "internal"}}, {}), _ok()],
    "b04": [(503, {"error": {"message": "overloaded"}}, {})],
    "b05": [(200, '{"object": "list", "data": [{"index": 0, "embedding": [0.1, 0.2', {})],
    "b06": [_ok()],
    "b07": [(200, "TRUNCATE", {})],
    "b08": [_ok()],
}


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def embed(text, dims):
    vec = [0.0] * dims
    for tok in tokens(text):
        vec[sum(map(ord, tok)) % dims] += 1.0
    return vec


class MockEmbeddingServer:
    def __init__(self):
        self.requests = []
        self.usage = []
        self.in_flight = 0
        self.peak_in_flight = 0
        self._attempts = {}
        self._lock = threading.Lock()
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._thread = threading.Thread(target=self._httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)

    @property
    def url(self):
        host, port = self._httpd.server_address
        return f"http://{host}:{port}"

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._httpd.shutdown()
        self._httpd.server_close()

    def requests_for(self, batch_id):
        return [r for r in self.requests if ((r["body"] or {}).get("metadata") or {}).get("batch_id") == batch_id]

    def _handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _reply(self, status, payload, headers=None):
                data = payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(data)

            def _record(self, body):
                parsed = urlparse(self.path)
                with server._lock:
                    server.requests.append({
                        "method": self.command,
                        "path": parsed.path,
                        "query": {k: v[0] for k, v in parse_qs(parsed.query).items()},
                        "authorization": self.headers.get("Authorization"),
                        "content_type": self.headers.get("Content-Type"),
                        "body": body,
                        "t": time.monotonic(),
                    })
                return parsed

            def _authorized(self):
                return self.headers.get("Authorization") == f"Bearer {API_KEY}"

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                try:
                    body = json.loads(self.rfile.read(length) or b"null")
                except json.JSONDecodeError:
                    body = None
                parsed = self._record(body)
                if parsed.path != "/v1/embeddings":
                    return self._reply(404, {"error": {"message": "not found"}})
                if not self._authorized():
                    return self._reply(401, {"error": {"message": "bad key"}})
                batch_id = ((body or {}).get("metadata") or {}).get("batch_id")
                if batch_id not in SCRIPT:
                    return self._reply(422, {"error": {"message": f"unknown batch_id {batch_id!r}"}})
                with server._lock:
                    server.in_flight += 1
                    server.peak_in_flight = max(server.peak_in_flight, server.in_flight)
                    n = server._attempts.get(batch_id, 0)
                    server._attempts[batch_id] = n + 1
                time.sleep(SERVICE_TIME_S)
                steps = SCRIPT[batch_id]
                status, payload, headers = steps[min(n, len(steps) - 1)]
                inputs = body.get("input") or []
                dims = int(body.get("dimensions") or 8)
                if status == 200 and (payload is None or payload == "TRUNCATE"):
                    vectors = [{"object": "embedding", "index": i, "embedding": embed(t, dims)}
                               for i, t in enumerate(inputs)]
                    if payload == "TRUNCATE":
                        vectors = vectors[:-1]
                    payload = {"object": "list", "model": body.get("model"), "data": vectors}
                with server._lock:
                    if status == 200:
                        server.usage.append({
                            "id": f"u{len(server.usage) + 1:03d}",
                            "batch_id": batch_id,
                            "total_tokens": sum(len(tokens(t)) for t in inputs),
                        })
                    server.in_flight -= 1
                self._reply(status, payload, headers)

            def do_GET(self):
                parsed = self._record(None)
                if parsed.path != "/v1/usage":
                    return self._reply(404, {"error": {"message": "not found"}})
                if not self._authorized():
                    return self._reply(401, {"error": {"message": "bad key"}})
                query = parse_qs(parsed.query)
                limit = int(query.get("limit", ["20"])[0])
                after = query.get("after", [""])[0]
                with server._lock:
                    remaining = [u for u in server.usage if u["id"] > after]
                rows = remaining[:limit]
                self._reply(200, {
                    "object": "list",
                    "data": rows,
                    "first_id": rows[0]["id"] if rows else None,
                    "last_id": rows[-1]["id"] if rows else None,
                    "has_more": len(remaining) > limit,
                })

        return Handler
