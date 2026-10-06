"""Local stand-in for the embeddings + vector index API. Test infrastructure: do not modify."""
import hashlib
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

API_KEY = "test-key"
DIMS = 48
LATENCY_S = 0.04

# batch index -> statuses served in order (the last one repeats)
SCRIPT = {
    0: [(200, {})],
    1: [(429, {"Retry-After": "2"}), (200, {})],
    2: [(503, {})],
    3: [(200, {})],
    4: [(500, {}), (200, {})],
}
# the index refuses these documents
CONFLICTS = {"d07"}


def tokens(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def embed(text):
    vec = [0] * DIMS
    for word in tokens(text):
        vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIMS] += 1
    return vec


class MockEmbeddingServer:
    def __init__(self):
        self.requests = []
        self.peak_in_flight = 0
        self._in_flight = 0
        self._attempts = {}
        self._versions = {}
        self._lock = threading.Lock()
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._httpd.daemon_threads = True
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

    def embed_requests(self, batch=None):
        return [r for r in self.requests if r["path"] == "/v1/embeddings"
                and (batch is None or ((r["body"] or {}).get("metadata") or {}).get("batch") == batch)]

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

            def _body(self):
                length = int(self.headers.get("Content-Length") or 0)
                try:
                    return json.loads(self.rfile.read(length) or b"null")
                except json.JSONDecodeError:
                    return None

            def _enter(self, body):
                with server._lock:
                    server.requests.append({"method": self.command, "path": urlparse(self.path).path,
                                            "auth": self.headers.get("Authorization"), "body": body})
                    server._in_flight += 1
                    server.peak_in_flight = max(server.peak_in_flight, server._in_flight)

            def _leave(self):
                with server._lock:
                    server._in_flight -= 1

            def do_POST(self):
                body = self._body()
                self._enter(body)
                try:
                    time.sleep(LATENCY_S)
                    self._embeddings(body)
                finally:
                    self._leave()

            def do_PUT(self):
                body = self._body()
                self._enter(body)
                try:
                    time.sleep(LATENCY_S / 4)
                    self._upsert(body)
                finally:
                    self._leave()

            def _embeddings(self, body):
                if urlparse(self.path).path != "/v1/embeddings":
                    return self._reply(404, {"error": {"message": "not found"}})
                if self.headers.get("Authorization") != f"Bearer {API_KEY}":
                    return self._reply(401, {"error": {"message": "bad key"}})
                batch = ((body or {}).get("metadata") or {}).get("batch")
                texts = (body or {}).get("input") or []
                if batch not in SCRIPT or not texts:
                    return self._reply(422, {"error": {"message": "bad request"}})
                with server._lock:
                    n = server._attempts.get(batch, 0)
                    server._attempts[batch] = n + 1
                    steps = SCRIPT[batch]
                    status, headers = steps[min(n, len(steps) - 1)]
                if status != 200:
                    return self._reply(status, {"error": {"message": "try again later"}}, headers)
                # items come back in reverse order; each carries its input index
                data = [{"index": i, "embedding": embed(t)} for i, t in enumerate(texts)][::-1]
                usage = {"prompt_tokens": sum(len(tokens(t)) for t in texts)}
                self._reply(200, {"model": body.get("model"), "data": data, "usage": usage})

            def _upsert(self, body):
                path = urlparse(self.path).path
                if not path.startswith("/v1/index/"):
                    return self._reply(404, {"error": {"message": "not found"}})
                doc_id = path.rsplit("/", 1)[-1]
                if doc_id in CONFLICTS:
                    return self._reply(409, {"error": {"message": "dimension mismatch with stored vector"}})
                with server._lock:
                    server._versions[doc_id] = server._versions.get(doc_id, 0) + 1
                    version = server._versions[doc_id]
                self._reply(200, {"doc_id": doc_id, "version": version})

        return Handler
