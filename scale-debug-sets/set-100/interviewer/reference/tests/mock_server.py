"""Scripted stand-in for the completion relay. Test infrastructure: do not modify."""
import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

API_KEY = "relay-test-key"
CHUNK_DELAY_S = 0.002

# prompt id -> the deltas of its answer, in seq order (seq starts at 1)
ANSWERS = {
    "p01": ["12", " times", " 12", " is", " 144", "."],
    "p02": ["Therefore", " Socrates", " is", " mortal", "."],
    "p03": ["The", " capital", " is", " Canberra", "."],
    "p04": ["Hold", " the", " reset button", " for", " ten", " seconds", "."],
    "p05": ["7", " plus", " 6", " is", " 12", "."],
    "p06": ["Hamlet", " was", " written", " by", " William", " Shakespeare", "."],
    "p08": ["The", " meeting", " covered", " hiring", ";", " budget approved", "."],
    "p10": ["The", " largest", " planet", " is"],
    "p12": ["Keep", " it", " sealed", " in", " a", " cool,", " ventilated", " cupboard", "."],
    "p13": ["Yes,", " it", " rained", "."],
    "p14": ["The", " symbol", " is", " Au", "."],
    "p16": ["6", " times", " 7", " is", " 41", "."],
}
# prompt id -> order in which seq numbers are put on the wire
DELIVERY = {
    "p02": [3, 1, 5, 2, 4],
    "p06": [1, 2, 3, 4, 3, 5, 6, 7],
}
# prompt id -> responses for successive attempts before the stream is served
ERRORS = {
    "p03": [(429, {"Retry-After": "1.5"}), (503, {})],
    "p07": [(400, {})] * 10,
    "p11": [(503, {})] * 10,
}
TRUNCATED = {"p10"}
POLICY = {"p04": True, "p09": False, "p12": True}

# oldest run first
BASELINES = [
    {"prompt_id": "p01", "run": "r1", "score": 1},
    {"prompt_id": "p05", "run": "r1", "score": 0},
    {"prompt_id": "P08", "run": "r1", "score": 1},
    {"prompt_id": "p02", "run": "r1", "score": 1},
    {"prompt_id": "p14", "run": "r1", "score": 1},
    {"prompt_id": "p05", "run": "r2", "score": 1},
    {"prompt_id": "p03", "run": "r2", "score": 1},
    {"prompt_id": "p06", "run": "r2", "score": 1},
    {"prompt_id": "p11", "run": "r2", "score": 1},
    {"prompt_id": "p04", "run": "r2", "score": 1},
    {"prompt_id": "p13 ", "run": "r2", "score": 1},
    {"prompt_id": "p12", "run": "r2", "score": 1},
    {"prompt_id": "p10", "run": "r2", "score": 0},
]


def _cursor(offset):
    return base64.urlsafe_b64encode(f"off={offset}".encode()).decode()


def _offset(cursor):
    return int(base64.urlsafe_b64decode(cursor.encode()).decode().split("=")[1])


class MockRelayServer:
    def __init__(self):
        self.requests = []
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

    def completions_for(self, prompt_id):
        return [r for r in self.requests if r["path"] == "/v1/complete" and r["prompt_id"] == prompt_id]

    def paths(self, prefix):
        return [r["path"] for r in self.requests if r["path"].startswith(prefix)]

    def _handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def _reply(self, status, payload, headers=None):
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for name, value in (headers or {}).items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(data)
                self.close_connection = True

            def _stream(self, events):
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                for event in events:
                    line = (json.dumps(event) + "\n").encode()
                    self.wfile.write(f"{len(line):x}\r\n".encode() + line + b"\r\n")
                    self.wfile.flush()
                    time.sleep(CHUNK_DELAY_S)
                self.wfile.write(b"0\r\n\r\n")
                self.close_connection = True

            def _log(self, body):
                entry = {
                    "method": self.command,
                    "path": urlparse(self.path).path,
                    "prompt_id": (body or {}).get("prompt_id"),
                    "request_id": self.headers.get("X-Request-Id"),
                    "authorization": self.headers.get("Authorization"),
                }
                with server._lock:
                    server.requests.append(entry)

            def _authorized(self):
                if self.headers.get("Authorization") != f"Bearer {API_KEY}":
                    self._reply(401, {"error": "unauthorized"})
                    return False
                return True

            def do_GET(self):
                self._log(None)
                if not self._authorized():
                    return
                url = urlparse(self.path)
                if url.path.startswith("/v1/policy/"):
                    prompt_id = url.path.rsplit("/", 1)[1]
                    if prompt_id not in POLICY:
                        return self._reply(404, {"error": "unknown prompt"})
                    return self._reply(200, {"prompt_id": prompt_id, "allowed": POLICY[prompt_id]})
                if url.path == "/v1/baselines":
                    query = parse_qs(url.query)
                    limit = int(query.get("limit", ["10"])[0])
                    cursor = query.get("cursor", [None])[0]
                    start = _offset(cursor) if cursor else 0
                    end = start + limit
                    return self._reply(200, {
                        "data": BASELINES[start:end],
                        "cursor": cursor,
                        "next_cursor": _cursor(end) if end < len(BASELINES) else None,
                    })
                self._reply(404, {"error": "not found"})

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                self._log(body)
                if not self._authorized():
                    return
                if urlparse(self.path).path != "/v1/complete":
                    return self._reply(404, {"error": "not found"})
                prompt_id = body.get("prompt_id")
                if body.get("model") != "relay-small" or prompt_id not in ANSWERS and prompt_id not in ERRORS:
                    return self._reply(400, {"error": "bad request"})
                with server._lock:
                    attempt = server._attempts.get(prompt_id, 0)
                    server._attempts[prompt_id] = attempt + 1
                script = ERRORS.get(prompt_id, [])
                if attempt < len(script):
                    status, headers = script[attempt]
                    return self._reply(status, {"error": f"relay returned {status}"}, headers)
                deltas = ANSWERS[prompt_id]
                budget = int(body.get("max_tokens", len(deltas)))
                sent = deltas[:budget]
                order = DELIVERY.get(prompt_id, range(1, len(sent) + 1))
                events = [{"seq": seq, "delta": sent[seq - 1]} for seq in order if seq <= len(sent)]
                if prompt_id not in TRUNCATED:
                    events.append({
                        "done": True,
                        "finish_reason": "length" if budget < len(deltas) else "stop",
                        "usage": {"completion_tokens": len(sent)},
                    })
                self._stream(events)

        return Handler
