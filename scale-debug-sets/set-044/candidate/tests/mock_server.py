"""Scripted stand-in for the embeddings endpoint. Test infrastructure: do not modify."""
import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

API_KEY = "emb-test-key"
LATENCY_S = 0.05

# batch id -> responses served in order (the last one repeats)
SCRIPT = {
    "b2": [(429, {"error": "rate limited"}, {"Retry-After": "0.2"}), (200, None, {})],
    "b4": [(503, {"error": "overloaded"}, {})],
    "b6": [(400, {"error": "input too long"}, {})],
}

INDEX_IDS = ["d01", "d02", "d04", "d07", "d08", "d31", "d10", "d12", "d40", "d27"]


def embed(text):
    return [float(len(text)), float(len(text.split())), float(sum(c in "aeiou" for c in text.lower()))]


def _cursor(offset):
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode()


def _offset(cursor):
    return int(base64.urlsafe_b64decode(cursor.encode()).decode().split(":")[1])


class MockEmbeddingServer:
    def __init__(self):
        self.requests = []
        self.in_flight = 0
        self.max_in_flight = 0
        self._attempts = {}
        self._lock = threading.Lock()
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._thread = threading.Thread(target=self._httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)

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

    def embed_calls(self, batch_id=None):
        calls = [r for r in self.requests if r["path"] == "/v1/embeddings"]
        if batch_id is not None:
            calls = [r for r in calls if ((r["body"] or {}).get("metadata") or {}).get("batch") == batch_id]
        return calls

    def _handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _reply(self, status, payload, headers=None):
                data = json.dumps(payload).encode()
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
                        "method": self.command, "path": parsed.path, "at": time.monotonic(),
                        "query": {k: v[0] for k, v in parse_qs(parsed.query).items()},
                        "auth": self.headers.get("Authorization"), "body": body,
                    })
                return parsed

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                try:
                    body = json.loads(self.rfile.read(length) or b"null")
                except json.JSONDecodeError:
                    body = None
                parsed = self._record(body)
                if parsed.path != "/v1/embeddings":
                    return self._reply(404, {"error": "not found"})
                if self.headers.get("Authorization") != f"Bearer {API_KEY}":
                    return self._reply(401, {"error": "bad key"})
                with server._lock:
                    server.in_flight += 1
                    server.max_in_flight = max(server.max_in_flight, server.in_flight)
                try:
                    time.sleep(LATENCY_S)
                    batch = ((body or {}).get("metadata") or {}).get("batch")
                    texts = (body or {}).get("input") or []
                    with server._lock:
                        n = server._attempts.get(batch, 0)
                        server._attempts[batch] = n + 1
                    steps = SCRIPT.get(batch, [(200, None, {})])
                    status, payload, headers = steps[min(n, len(steps) - 1)]
                    if status == 200:
                        payload = {
                            "model": body.get("model"),
                            "data": [{"index": i, "embedding": embed(t)} for i, t in reversed(list(enumerate(texts)))],
                            "usage": {"total_tokens": sum(len(t.split()) for t in texts)},
                        }
                finally:
                    with server._lock:
                        server.in_flight -= 1
                self._reply(status, payload, headers)

            def do_GET(self):
                parsed = self._record(None)
                if parsed.path != "/v1/index":
                    return self._reply(404, {"error": "not found"})
                if self.headers.get("Authorization") != f"Bearer {API_KEY}":
                    return self._reply(401, {"error": "bad key"})
                query = parse_qs(parsed.query)
                limit = int(query.get("limit", ["10"])[0])
                offset = _offset(query["cursor"][0]) if "cursor" in query else 0
                rows = INDEX_IDS[offset:offset + limit]
                more = offset + limit < len(INDEX_IDS)
                self._reply(200, {"ids": rows, "next_cursor": _cursor(offset + limit) if more else None})

        return Handler
