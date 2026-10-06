"""Scripted stand-in for the embeddings endpoint. Test infrastructure: do not modify."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

API_KEY = "test-key"
WORK_S = 0.08  # simulated model time per request

# batch_id -> responses served in order (the last one repeats). "reverse" = data items out of order.
SCRIPT = {
    "b01": [(200, {}, None)],
    "b02": [(429, {"Retry-After": "0.3"}, None), (200, {}, None)],
    "b03": [(200, {}, "reverse")],
    "b04": [(503, {}, None)],
    "b05": [(400, {}, None)],
    "b06": [(500, {}, None), (200, {}, None)],
    "b07": [(200, {}, None)],
}


def embed(text):
    words = text.split()
    return [len(words), sum(len(w) for w in words) % 10, len(set(text.lower()) & set("aeiou"))]


def tokens(texts):
    return sum(len(t.split()) + 2 for t in texts)


class MockEmbeddingServer:
    def __init__(self):
        self.requests = []
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

    def requests_for(self, batch_id):
        return [r for r in self.requests if ((r["body"] or {}).get("metadata") or {}).get("batch_id") == batch_id]

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

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length)
                try:
                    body = json.loads(raw or b"null")
                except json.JSONDecodeError:
                    body = None
                with server._lock:
                    server.requests.append({"path": self.path, "at": time.monotonic(), "body": body,
                                            "authorization": self.headers.get("Authorization")})
                    server.in_flight += 1
                    server.max_in_flight = max(server.max_in_flight, server.in_flight)
                try:
                    time.sleep(WORK_S)
                    self._respond(body)
                finally:
                    with server._lock:
                        server.in_flight -= 1

            def _respond(self, body):
                if self.path != "/v1/embeddings":
                    return self._reply(404, {"error": {"message": "not found"}})
                if self.headers.get("Authorization") != f"Bearer {API_KEY}":
                    return self._reply(401, {"error": {"message": "bad key"}})
                batch_id = ((body or {}).get("metadata") or {}).get("batch_id")
                if batch_id not in SCRIPT:
                    return self._reply(422, {"error": {"message": f"unknown batch {batch_id!r}"}})
                with server._lock:
                    n = server._attempts.get(batch_id, 0)
                    server._attempts[batch_id] = n + 1
                steps = SCRIPT[batch_id]
                status, headers, mode = steps[min(n, len(steps) - 1)]
                if status != 200:
                    return self._reply(status, {"error": {"message": f"HTTP {status}"}}, headers)
                texts = body["input"]
                data = [{"index": i, "embedding": embed(t)} for i, t in enumerate(texts)]
                if mode == "reverse":
                    data.reverse()
                self._reply(200, {"data": data, "usage": {"total_tokens": tokens(texts)}}, headers)

        return Handler
