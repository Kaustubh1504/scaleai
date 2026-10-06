"""Scripted stand-in for the embeddings API and vector index. Test infrastructure: do not modify."""
import base64
import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

API_KEY = "sk-test-embed"
HOLD_SECONDS = 0.04


def _sha1(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


# batch_id -> (status, headers) served in order before success; "products-1" never recovers
SCRIPT = {
    "faq-1": [(429, {"Retry-After": "0.25"})],
    "policies-0": [(500, {})],
    "products-1": [(503, {})] * 10,
}

INDEX = {
    "faq": [],
    "products": [],
    "policies": [
        {"doc_id": "p01", "sha1": _sha1("Refunds are issued within 14 days of a return.")},
        {"doc_id": "p02", "sha1": _sha1("Annotators must complete security training yearly.")},
        {"doc_id": "p03", "sha1": _sha1("Personal data is deleted after 90 days.")},
        {"doc_id": "p04", "sha1": _sha1("Contractors are paid every month.")},
        {"doc_id": "p05", "sha1": _sha1("Escalations go to the on-call lead first.")},
        {"doc_id": "p41", "sha1": _sha1("Legacy travel policy.")},
        {"doc_id": "p42", "sha1": _sha1("Legacy laptop policy.")},
        {"doc_id": "p43", "sha1": _sha1("Legacy badge policy.")},
        {"doc_id": "p06", "sha1": _sha1("Overtime requires written approval.")},
        {"doc_id": "p88", "sha1": _sha1("Draft policy placeholder.")},
    ],
}


def _vector(text):
    return [float(len(text)), float(len(text.split()))]


def _tokens(texts):
    return sum(len(t.split()) + 2 for t in texts)


def _token(offset):
    return base64.urlsafe_b64encode(f"o{offset}".encode()).decode()


def _offset(token):
    return int(base64.urlsafe_b64decode(token.encode()).decode()[1:])


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

    def embedding_requests(self, batch_id=None):
        rows = [r for r in self.requests if r["path"] == "/v1/embeddings"]
        if batch_id is not None:
            rows = [r for r in rows if ((r["body"] or {}).get("metadata") or {}).get("batch_id") == batch_id]
        return rows

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
                    time.sleep(HOLD_SECONDS)
                    batch_id = ((body or {}).get("metadata") or {}).get("batch_id")
                    texts = (body or {}).get("input") or []
                    with server._lock:
                        n = server._attempts.get(batch_id, 0)
                        server._attempts[batch_id] = n + 1
                    script = SCRIPT.get(batch_id, [])
                    if n < len(script):
                        status, headers = script[n]
                        return self._reply(status, {"error": {"message": "temporarily unavailable"}}, headers)
                    # items come back newest-first; clients must use "index"
                    data = [{"index": i, "embedding": _vector(t)} for i, t in enumerate(texts)][::-1]
                    tokens = _tokens(texts)
                    self._reply(200, {"data": data, "usage": {"prompt_tokens": tokens, "total_tokens": tokens}})
                finally:
                    with server._lock:
                        server.in_flight -= 1

            def do_GET(self):
                parsed = self._record(None)
                if not parsed.path.startswith("/v1/index/"):
                    return self._reply(404, {"error": {"message": "not found"}})
                if not self._authorized():
                    return self._reply(401, {"error": {"message": "bad key"}})
                collection = unquote(parsed.path[len("/v1/index/"):])
                if collection not in INDEX:
                    return self._reply(404, {"error": {"message": f"no index {collection!r}"}})
                query = parse_qs(parsed.query)
                limit = int(query.get("limit", ["10"])[0])
                offset = _offset(query["page_token"][0]) if "page_token" in query else 0
                rows = INDEX[collection][offset:offset + limit]
                more = offset + limit < len(INDEX[collection])
                self._reply(200, {"items": rows, "next_page_token": _token(offset + limit) if more else None})

        return Handler
