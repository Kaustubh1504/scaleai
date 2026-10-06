"""Scripted stand-in for the embeddings endpoint. Test infrastructure: do not modify."""
import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

API_KEY = "test-key"
DIMS = {"embed-s": 4, "embed-l": 8}
MAX_INPUT_CHARS = {"embed-s": 60}
SERVER_PAGE_CAP = 4
LATENCY_S = 0.04

# (model, word that triggers the script) -> responses served in order (the last one repeats)
SCRIPT = {
    ("embed-s", "refund"): [(429, {"error": {"message": "rate limited"}}, {"Retry-After": "1"}), ("ok", None, {})],
    ("embed-l", "warranty"): [(503, {"error": {"message": "overloaded"}}, {}),
                              (503, {"error": {"message": "overloaded"}}, {}),
                              ("ok", None, {})],
    ("embed-l", "invoice"): [("short", None, {})],
}


def vector(model, text):
    seed = sum(ord(c) for c in text)
    return [round(((seed * (i + 3)) % 97) / 97, 4) for i in range(DIMS[model])]


def _cursor(offset):
    return base64.urlsafe_b64encode(f"offset:{offset}".encode()).decode()


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

    def posts(self, model=None):
        return [r for r in self.requests
                if r["method"] == "POST" and (model is None or (r["body"] or {}).get("model") == model)]

    def _respond_embeddings(self, body):
        model, inputs = body.get("model"), body.get("input")
        if model not in DIMS or not isinstance(inputs, list) or not inputs:
            return 400, {"error": {"message": "bad request"}}, {}
        limit = MAX_INPUT_CHARS.get(model)
        if limit and any(len(t) > limit for t in inputs):
            return 400, {"error": {"message": f"input too long for {model}"}}, {}
        step = ("ok", None, {})
        for (m, word), steps in SCRIPT.items():
            if m == model and any(word in t.lower() for t in inputs):
                key = (m, word)
                with self._lock:
                    n = self._attempts.get(key, 0)
                    self._attempts[key] = n + 1
                step = steps[min(n, len(steps) - 1)]
                break
        status, payload, headers = step
        if status not in ("ok", "short"):
            return status, payload, headers
        data = [{"index": i, "embedding": vector(model, t)} for i, t in enumerate(inputs)]
        if model == "embed-l":
            data.reverse()
        if status == "short":
            data = data[1:]
        tokens = sum(len(t.split()) for t in inputs)
        with self._lock:
            self.usage.append({"model": model, "first_input": inputs[0], "tokens": tokens})
        return 200, {"data": data, "usage": {"tokens": tokens}}, {}

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
                with server._lock:
                    server.in_flight += 1
                    server.max_in_flight = max(server.max_in_flight, server.in_flight)
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                    try:
                        body = json.loads(self.rfile.read(length) or b"null")
                    except json.JSONDecodeError:
                        body = None
                    parsed = self._record(body)
                    time.sleep(LATENCY_S)
                    if parsed.path != "/v1/embeddings":
                        return self._reply(404, {"error": {"message": "not found"}})
                    if not self._authorized():
                        return self._reply(401, {"error": {"message": "bad key"}})
                    self._reply(*server._respond_embeddings(body or {}))
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
                limit = min(int(query.get("limit", ["10"])[0]), SERVER_PAGE_CAP)
                offset = _offset(query["cursor"][0]) if "cursor" in query else 0
                with server._lock:
                    ordered = sorted(server.usage, key=lambda u: (u["model"], u["first_input"]))
                rows = ordered[offset:offset + limit]
                more = offset + limit < len(ordered)
                self._reply(200, {"data": rows, "next_cursor": _cursor(offset + limit) if more else None})

        return Handler
