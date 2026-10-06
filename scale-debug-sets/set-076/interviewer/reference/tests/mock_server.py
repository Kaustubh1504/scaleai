"""Scripted stand-in for the embeddings service. Test infrastructure: do not modify."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

API_KEY = "test-key"
HANDLE_DELAY_S = 0.03
MAX_PAGE = 3  # the service never returns more than this many items per page

# batch_id -> (status, headers, dims_override) served in order (the last one repeats)
SCRIPT = {
    "faq-02": [(429, {"Retry-After": "0"}, None), (429, {"Retry-After": "0"}, None), (200, {}, None)],
    "policies-01": [(503, {}, None)],
    "policies-02": [(500, {}, None), (200, {}, None)],
    "changelog-01": [(200, {}, 5)],
    "pricing-01": [(400, {}, None)],
}
DEFAULT_STEP = [(200, {}, None)]

# vectors that already exist before the job runs
SEEDED = {"faq": ["faq-legacy-1", "faq-legacy-2"], "policies": ["pol-100"]}


class MockEmbeddingServer:
    def __init__(self):
        self.requests = []
        self.commits = []
        self.max_in_flight = 0
        self._in_flight = 0
        self._attempts = {}
        self._vectors = {k: set(v) for k, v in SEEDED.items()}
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

    def embedding_requests(self, batch_id=None):
        return [r for r in self.requests if r["path"] == "/v1/embeddings"
                and (batch_id is None or (r["body"] or {}).get("batch_id") == batch_id)]

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
                if not self._authorized():
                    return self._reply(401, {"error": "bad key"})
                if parsed.path.startswith("/v1/jobs/") and parsed.path.endswith("/commit"):
                    job = unquote(parsed.path[len("/v1/jobs/"):-len("/commit")])
                    with server._lock:
                        server.commits.append({"job_id": job, **(body or {})})
                    return self._reply(200, {"status": "committed"})
                if parsed.path != "/v1/embeddings":
                    return self._reply(404, {"error": "not found"})
                body = body or {}
                bid = body.get("batch_id")
                with server._lock:
                    server._in_flight += 1
                    server.max_in_flight = max(server.max_in_flight, server._in_flight)
                    n = server._attempts.get(bid, 0)
                    server._attempts[bid] = n + 1
                    steps = SCRIPT.get(bid, DEFAULT_STEP)
                    status, headers, dims_override = steps[min(n, len(steps) - 1)]
                time.sleep(HANDLE_DELAY_S)
                items = body.get("input") or []
                dims = dims_override or int(body.get("dimensions") or 4)
                if status == 200:
                    payload = {"data": [{"index": i, "embedding": [0.1 * (i + 1)] * dims} for i in range(len(items))],
                               "usage": {"tokens": sum(len(it["text"].split()) for it in items)}}
                else:
                    payload = {"error": {"code": status}}
                with server._lock:
                    if status == 200 and dims_override is None:
                        server._vectors.setdefault(body.get("collection"), set()).update(it["id"] for it in items)
                    server._in_flight -= 1
                self._reply(status, payload, headers)

            def do_GET(self):
                parsed = self._record(None)
                if not self._authorized():
                    return self._reply(401, {"error": "bad key"})
                parts = parsed.path.strip("/").split("/")
                if len(parts) != 4 or parts[:2] != ["v1", "collections"] or parts[3] != "vectors":
                    return self._reply(404, {"error": "not found"})
                query = parse_qs(parsed.query)
                offset = int(query.get("offset", ["0"])[0])
                limit = min(int(query.get("limit", [str(MAX_PAGE)])[0]), MAX_PAGE)
                with server._lock:
                    ids = sorted(server._vectors.get(unquote(parts[2]), set()))
                rows = [{"id": i} for i in ids[offset:offset + limit]]
                self._reply(200, {"items": rows, "has_more": offset + len(rows) < len(ids)})

        return Handler
