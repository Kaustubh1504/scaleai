"""Scripted stand-in for the batch embedding API. Test infrastructure: do not modify."""
import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

API_KEY = "test-key"
MAX_INPUT_CHARS = 120
LATENCY_S = 0.02

# collection -> statuses returned for successive create attempts before the 202
CREATE_SCRIPT = {
    "legal": [(429, {"error": {"type": "rate_limited", "retry_after_ms": 120}})],
    "product": [(500, {"error": {"type": "server_error"}}), (503, {"error": {"type": "overloaded"}})],
}
# collection -> number of status polls before the job reports a final state
POLLS_TO_FINISH = {"news": 4}


def _embed(text):
    words = text.split()
    vowels = sum(text.lower().count(v) for v in "aeiou")
    return [len(words), vowels, len(text) % 10, 1 + sum(map(ord, text)) % 5]


def _token(offset):
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode()


def _offset(token):
    return int(base64.urlsafe_b64decode(token.encode()).decode().split(":")[1])


class MockBatchServer:
    def __init__(self):
        self.requests = []
        self.max_inflight = 0
        self._inflight = 0
        self._creates = {}
        self._jobs = {}
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

    def creates_for(self, collection):
        return [r for r in self.requests if r["method"] == "POST" and (r["body"] or {}).get("collection") == collection]

    def job_id_for(self, collection, first_doc):
        for job_id, job in self._jobs.items():
            if job["collection"] == collection and job["inputs"][0]["id"] == first_doc:
                return job_id
        return None

    def polls_for(self, job_id):
        return [r for r in self.requests if r["method"] == "GET" and r["path"] == f"/v1/batches/{job_id}"]

    def _handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _reply(self, status, payload):
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _enter(self, body):
                parsed = urlparse(self.path)
                with server._lock:
                    server._inflight += 1
                    server.max_inflight = max(server.max_inflight, server._inflight)
                    server.requests.append({
                        "method": self.command, "path": parsed.path,
                        "query": {k: v[0] for k, v in parse_qs(parsed.query).items()},
                        "authorization": self.headers.get("Authorization"), "body": body,
                    })
                time.sleep(LATENCY_S)
                return parsed

            def _leave(self):
                with server._lock:
                    server._inflight -= 1

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                try:
                    body = json.loads(self.rfile.read(length) or b"null")
                except json.JSONDecodeError:
                    body = None
                parsed = self._enter(body)
                try:
                    self._create(parsed, body or {})
                finally:
                    self._leave()

            def do_GET(self):
                parsed = self._enter(None)
                try:
                    self._get(parsed)
                finally:
                    self._leave()

            def _create(self, parsed, body):
                if parsed.path != "/v1/batches":
                    return self._reply(404, {"error": {"type": "not_found"}})
                if self.headers.get("Authorization") != f"Bearer {API_KEY}":
                    return self._reply(401, {"error": {"type": "unauthorized"}})
                collection = body.get("collection")
                inputs = body.get("inputs") or []
                if not inputs or not body.get("model"):
                    return self._reply(400, {"error": {"type": "invalid_request"}})
                with server._lock:
                    n = server._creates.get(collection, 0)
                    server._creates[collection] = n + 1
                    script = CREATE_SCRIPT.get(collection, [])
                    if n < len(script):
                        status, payload = script[n]
                        failure = (status, payload)
                    else:
                        failure = None
                        job_id = f"bt_{len(server._jobs) + 1:03d}"
                        too_long = any(len(i.get("text", "")) > MAX_INPUT_CHARS for i in inputs)
                        server._jobs[job_id] = {"collection": collection, "inputs": inputs, "polls": 0,
                                                "error": "input_too_long" if too_long else None}
                if failure:
                    return self._reply(*failure)
                self._reply(202, {"id": job_id, "status": "queued"})

            def _get(self, parsed):
                if self.headers.get("Authorization") != f"Bearer {API_KEY}":
                    return self._reply(401, {"error": {"type": "unauthorized"}})
                parts = parsed.path.strip("/").split("/")
                if len(parts) < 3 or parts[:2] != ["v1", "batches"] or parts[2] not in server._jobs:
                    return self._reply(404, {"error": {"type": "not_found"}})
                job = server._jobs[parts[2]]
                if len(parts) == 3:
                    with server._lock:
                        job["polls"] += 1
                        done = job["polls"] >= POLLS_TO_FINISH.get(job["collection"], 1)
                    if not done:
                        return self._reply(200, {"id": parts[2], "status": "running" if job["polls"] > 1 else "queued"})
                    if job["error"]:
                        return self._reply(200, {"id": parts[2], "status": "failed", "error": {"code": job["error"]}})
                    return self._reply(200, {"id": parts[2], "status": "completed"})
                if parts[3:] != ["results"] or job["error"]:
                    return self._reply(404, {"error": {"type": "not_found"}})
                query = parse_qs(parsed.query)
                size = int(query.get("page_size", ["10"])[0])
                token = query.get("page_token", [None])[0]
                start = _offset(token) if token else 0
                rows = [{"id": i["id"], "embedding": _embed(i["text"])} for i in job["inputs"][start:start + size]]
                more = start + size < len(job["inputs"])
                self._reply(200, {"results": rows, "page_token": token,
                                  "next_page_token": _token(start + size) if more else None})

        return Handler
