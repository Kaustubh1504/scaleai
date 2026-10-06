"""Scripted stand-in for the dataset + embeddings + index API. Test infrastructure: do not modify."""
import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

API_KEY = "test-key"
DATASET = "support-faq"
RECORDS = json.loads((Path(__file__).resolve().parent.parent / "data" / "records.json").read_text())
LATENCY_S = 0.05

# batch_id -> responses served in order (the last one repeats). None means "embed normally".
SCRIPT = {
    "b2": [(503, {"error": {"message": "overloaded"}}, {}), (503, {"error": {"message": "overloaded"}}, {}), None],
    "b3": [(429, {"error": {"message": "rate limited"}}, {"Retry-After": "0"}), None],
    "b5": [(400, {"error": {"message": "input too long"}}, {})],
}
SHORT_VECTORS = {"b4"}
REVERSED = {"b1"}
UPSERT_FAILS = {"b6"}


def embed(text, dims=4):
    vec = [float(len(text)), float(text.count(" ")), float(sum(map(ord, text)) % 97), float(len(set(text.lower())))]
    return vec[:dims]


def _token(offset):
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode()


def _offset(token):
    return int(base64.urlsafe_b64decode(token.encode()).decode().split(":")[1])


class MockApiServer:
    def __init__(self):
        self.requests = []
        self.upserts = []
        self.max_in_flight = 0
        self._in_flight = 0
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

    def embedding_requests(self, batch_id=None):
        return [r for r in self.requests if r["path"] == "/v1/embeddings"
                and (batch_id is None or ((r["body"] or {}).get("metadata") or {}).get("batch_id") == batch_id)]

    def page_requests(self):
        return [r for r in self.requests if r["path"].endswith("/records")]

    def _embeddings(self, body):
        bid = ((body or {}).get("metadata") or {}).get("batch_id")
        with self._lock:
            n = self._attempts.get(bid, 0)
            self._attempts[bid] = n + 1
        steps = SCRIPT.get(bid, [None])
        step = steps[min(n, len(steps) - 1)]
        if step is not None:
            return step
        texts = body.get("input") or []
        dims = int(body.get("dimensions", 4)) - (1 if bid in SHORT_VECTORS else 0)
        data = [{"object": "embedding", "index": i, "embedding": embed(t, dims)} for i, t in enumerate(texts)]
        if bid in REVERSED:
            data.reverse()
        usage = {"total_tokens": sum(len(t.split()) for t in texts)}
        return 200, {"object": "list", "data": data, "model": body.get("model"), "usage": usage}, {}

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
                        "at": time.monotonic(),
                    })
                return parsed

            def _authorized(self):
                return self.headers.get("Authorization") == f"Bearer {API_KEY}"

            def do_GET(self):
                parsed = self._record(None)
                if parsed.path != f"/v1/datasets/{DATASET}/records":
                    return self._reply(404, {"error": {"message": "not found"}})
                if not self._authorized():
                    return self._reply(401, {"error": {"message": "bad key"}})
                query = parse_qs(parsed.query)
                limit = int(query.get("limit", ["10"])[0])
                offset = _offset(query["page_token"][0]) if "page_token" in query else 0
                rows = RECORDS[offset:offset + limit]
                more = offset + limit < len(RECORDS)
                self._reply(200, {"records": rows, "next_page_token": _token(offset + limit) if more else None})

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                try:
                    body = json.loads(self.rfile.read(length) or b"null")
                except json.JSONDecodeError:
                    body = None
                parsed = self._record(body)
                if not self._authorized():
                    return self._reply(401, {"error": {"message": "bad key"}})
                if parsed.path == "/v1/embeddings":
                    with server._lock:
                        server._in_flight += 1
                        server.max_in_flight = max(server.max_in_flight, server._in_flight)
                    try:
                        time.sleep(LATENCY_S)
                        status, payload, headers = server._embeddings(body)
                    finally:
                        with server._lock:
                            server._in_flight -= 1
                    return self._reply(status, payload, headers)
                if parsed.path == "/v1/index/upsert":
                    bid = (body or {}).get("batch_id")
                    if bid in UPSERT_FAILS:
                        return self._reply(500, {"error": {"message": "index unavailable"}})
                    with server._lock:
                        server.upserts.append(bid)
                    return self._reply(200, {"upserted": len((body or {}).get("items") or [])})
                self._reply(404, {"error": {"message": "not found"}})

        return Handler
