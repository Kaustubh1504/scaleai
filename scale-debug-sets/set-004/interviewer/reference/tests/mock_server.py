"""Scripted stand-in for the model endpoint. Test infrastructure: do not modify."""
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

API_KEY = "test-key"


def _chat(content):
    return {"choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}]}


# request_id -> responses served in order (the last one repeats)
SCRIPT = {
    "r01": [(200, _chat('{"score": 8, "passed": true}'), {})],
    "r02": [(200, _chat('Here is my grade:\n```json\n{"score": 3, "passed": "false"}\n```'), {})],
    "r03": [(429, {"error": {"message": "rate limited"}}, {"Retry-After": "0"})] * 3
           + [(200, _chat('{"score": 6, "passed": true, "rubric": {"accuracy": 3, "style": 3}}'), {})],
    "r04": [(500, {"error": {"message": "internal"}}, {}),
            (200, _chat('{"score": 9, "passed": true}'), {})],
    "r05": [(400, {"error": {"message": "prompt too long"}}, {})],
    "r06": [(200, _chat("I cannot grade this answer."), {})],
    "r07": [(503, {"error": {"message": "overloaded"}}, {})],
    "r08": [(200, _chat('```json\n{"score": 7.5, "passed": "TRUE"}\n```'), {})],
    "r09": [(200, _chat('{"score": 2, "passed": false}'), {})],
    "r10": [(429, {"error": {"message": "rate limited"}}, {"Retry-After": "0"}),
            (200, _chat('{"score": 10, "passed": true}'), {})],
}

USAGE = {
    "r01": (820, 412), "r02": (1430, 388), "r03": (650, 501), "r04": (2210, 450),
    "r06": (300, 120), "r08": (980, 397), "r09": (1105, 405), "r10": (540, 366),
}


def _cursor(offset):
    return base64.urlsafe_b64encode(f"offset:{offset}".encode()).decode()


def _offset(cursor):
    return int(base64.urlsafe_b64decode(cursor.encode()).decode().split(":")[1])


class MockModelServer:
    def __init__(self):
        self.requests = []
        self.usage = []
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

    def requests_for(self, request_id):
        return [r for r in self.requests if (r["body"] or {}).get("metadata", {}).get("request_id") == request_id]

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
                        "headers": {"authorization": self.headers.get("Authorization"),
                                    "content-type": self.headers.get("Content-Type")},
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
                if parsed.path != "/v1/chat/completions":
                    return self._reply(404, {"error": {"message": "not found"}})
                if not self._authorized():
                    return self._reply(401, {"error": {"message": "bad key"}})
                rid = ((body or {}).get("metadata") or {}).get("request_id")
                if rid not in SCRIPT:
                    return self._reply(422, {"error": {"message": f"unknown request_id {rid!r}"}})
                with server._lock:
                    n = server._attempts.get(rid, 0)
                    server._attempts[rid] = n + 1
                    steps = SCRIPT[rid]
                    status, payload, headers = steps[min(n, len(steps) - 1)]
                    if status == 200:
                        latency, tokens = USAGE[rid]
                        server.usage.append({"request_id": rid, "latency_ms": latency, "total_tokens": tokens})
                self._reply(status, payload, headers)

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
