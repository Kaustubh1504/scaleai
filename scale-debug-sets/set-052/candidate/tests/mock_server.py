"""Scripted stand-in for the embeddings endpoint. Test infrastructure: do not modify."""
import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

API_KEY = "test-key"
POST_DELAY_S = 0.04

# batch id (the request's "user" field) -> responses served in order (the last one repeats).
# None means "embed the input normally".
SCRIPT = {
    "faq-02": [(429, {"error": {"message": "rate limited"}}, {"Retry-After": "0.01"}), None],
    "kb-01": [(503, {"error": {"message": "overloaded"}}, {}),
              (503, {"error": {"message": "overloaded"}}, {}), None],
    "kb-02": [(422, {"error": {"message": "input 3 exceeds the context window"}}, {})],
    "policies-01": [(503, {"error": {"message": "overloaded"}}, {})],
}


def embed(text):
    """Deterministic 4-d embedding: length, vowels, words, character checksum."""
    vowels = sum(1 for c in text.lower() if c in "aeiou")
    return [float(len(text)), float(vowels), float(len(text.split())), float(sum(map(ord, text)) % 97)]


def _cursor(offset):
    return base64.urlsafe_b64encode(f"usage:{offset}".encode()).decode()


def _offset(cursor):
    return int(base64.urlsafe_b64decode(cursor.encode()).decode().split(":")[1])


class MockEmbeddingServer:
    def __init__(self):
        self.requests = []
        self.usage = []
        self.in_flight = 0
        self.max_in_flight = 0
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

    def posts_for(self, batch_id):
        return [r for r in self.requests if r["method"] == "POST" and (r["body"] or {}).get("user") == batch_id]

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
                        "method": self.command,
                        "path": parsed.path,
                        "query": {k: v[0] for k, v in parse_qs(parsed.query).items()},
                        "authorization": self.headers.get("Authorization"),
                        "body": body,
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
                with server._lock:
                    server.in_flight += 1
                    server.max_in_flight = max(server.max_in_flight, server.in_flight)
                try:
                    time.sleep(POST_DELAY_S)
                    batch_id = (body or {}).get("user")
                    with server._lock:
                        n = server._attempts.get(batch_id, 0)
                        server._attempts[batch_id] = n + 1
                    steps = SCRIPT.get(batch_id, [None])
                    step = steps[min(n, len(steps) - 1)]
                    if step is not None:
                        return self._reply(*step)
                    inputs = body["input"]
                    tokens = sum(len(text.split()) for text in inputs)
                    with server._lock:
                        server.usage.append({"batch": batch_id, "total_tokens": tokens})
                    data = [{"object": "embedding", "index": i, "embedding": embed(t)} for i, t in enumerate(inputs)]
                    data.reverse()  # the real service does not promise any order
                    self._reply(200, {"object": "list", "data": data, "model": body.get("model"),
                                      "usage": {"total_tokens": tokens}})
                finally:
                    with server._lock:
                        server.in_flight -= 1

            def do_GET(self):
                parsed = self._record(None)
                if parsed.path != "/v1/usage":
                    return self._reply(404, {"error": {"message": "not found"}})
                if not self._authorized():
                    return self._reply(401, {"error": {"message": "bad key"}})
                query = parse_qs(parsed.query)
                limit = int(query.get("limit", ["10"])[0])
                offset = _offset(query["cursor"][0]) if "cursor" in query else 0
                with server._lock:
                    rows = server.usage[offset:offset + limit]
                    more = offset + limit < len(server.usage)
                self._reply(200, {"data": rows, "next_cursor": _cursor(offset + limit) if more else None})

        return Handler
