"""Scripted stand-in for the batch classification API. Test infrastructure: do not modify."""
import json
import math
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

API_KEY = "batch-test-key"
SUBMIT_DELAY_S = 0.12

# shard -> statuses served for the submit call, in order (the last one repeats)
SUBMIT_SCRIPT = {"S3": [429, 201]}
# shard -> number of "in_progress" polls before the terminal status
POLLS = {"S1": 1, "S2": 2, "S3": 0, "S4": 1, "S5": 3}
TERMINAL = {"S1": "completed", "S2": "completed", "S3": "completed", "S4": "failed", "S5": "completed"}
TOKENS = {"S1": 1840, "S2": 4210, "S3": 1505, "S5": 1260}

LABELS = {
    "R01": ("cat", 0.95), "R02": ("dog", 0.88), "R03": ("cat", 0.41),
    "R04": ("dog", 0.91), "R05": ("bird", 0.77), "R06": ("cat", 0.83), "R07": ("dog", 0.52),
    "R08": ("bird", 0.99), "R09": ("cat", 0.74), "R10": ("dog", 0.86),
    "R11": ("bird", 0.93), "R12": ("cat", 0.7), "R13": ("dog", 0.69),
    "R14": ("cat", 0.9), "R15": ("dog", 0.9),
    "R16": ("bird", 0.81), "R17": ("cat", 0.97), "R19": ("dog", 0.6),
}


class MockBatchServer:
    def __init__(self):
        self.requests = []
        self.batches = {}
        self.archived = []
        self.inflight = 0
        self.peak_inflight = 0
        self._submits = {}
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

    def submits_for(self, shard):
        return [r for r in self.requests
                if r["method"] == "POST" and (r["body"] or {}).get("shard") == shard]

    def _handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _reply(self, status, payload=None, headers=None):
                data = json.dumps(payload).encode() if payload is not None else b""
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(data)

            def _record(self, body=None):
                parsed = urlparse(self.path)
                with server._lock:
                    server.requests.append({
                        "method": self.command,
                        "path": parsed.path,
                        "query": {k: v[0] for k, v in parse_qs(parsed.query).items()},
                        "auth": self.headers.get("Authorization"),
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
                if parsed.path != "/v1/batches":
                    return self._reply(404, {"error": "not found"})
                if not self._authorized():
                    return self._reply(401, {"error": "bad key"})
                shard = (body or {}).get("shard")
                if shard not in POLLS:
                    return self._reply(422, {"error": f"unknown shard {shard!r}"})
                with server._lock:
                    server.inflight += 1
                    server.peak_inflight = max(server.peak_inflight, server.inflight)
                time.sleep(SUBMIT_DELAY_S)
                with server._lock:
                    server.inflight -= 1
                    n = server._submits.get(shard, 0)
                    server._submits[shard] = n + 1
                    steps = SUBMIT_SCRIPT.get(shard, [201])
                    status = steps[min(n, len(steps) - 1)]
                    if status != 201:
                        return self._reply(status, {"error": "rate limited"}, {"Retry-After": "0"})
                    batch_id = f"batch_{shard.lower()}"
                    server.batches[batch_id] = {"shard": shard, "inputs": body.get("inputs", []), "polls": 0}
                self._reply(201, {"id": batch_id, "status": "queued"})

            def do_GET(self):
                parsed = self._record()
                if not self._authorized():
                    return self._reply(401, {"error": "bad key"})
                match = re.fullmatch(r"/v1/batches/([\w-]+)(/results)?", parsed.path)
                batch = server.batches.get(match.group(1)) if match else None
                if batch is None:
                    return self._reply(404, {"error": "not found"})
                shard = batch["shard"]
                if match.group(2) is None:
                    with server._lock:
                        batch["polls"] += 1
                        done = batch["polls"] > POLLS[shard]
                    if not done:
                        return self._reply(200, {"id": match.group(1), "status": "in_progress"})
                    payload = {"id": match.group(1), "status": TERMINAL[shard]}
                    if TERMINAL[shard] == "completed":
                        payload["usage"] = {"total_tokens": TOKENS[shard]}
                    return self._reply(200, payload)
                if TERMINAL[shard] != "completed" or batch["polls"] <= POLLS[shard]:
                    return self._reply(409, {"error": "batch not completed"})
                query = parse_qs(parsed.query)
                limit = int(query.get("limit", ["10"])[0])
                page = int(query.get("page", ["1"])[0])
                rows = []
                for item in batch["inputs"]:
                    label, score = LABELS.get(item.get("id"), ("unknown", 0.0))
                    rows.append({"id": item.get("id"), "label": label, "score": score})
                total_pages = max(1, math.ceil(len(rows) / limit))
                start = (page - 1) * limit
                self._reply(200, {"data": rows[start:start + limit], "page": page, "total_pages": total_pages})

            def do_DELETE(self):
                parsed = self._record()
                if not self._authorized():
                    return self._reply(401, {"error": "bad key"})
                batch_id = parsed.path.rsplit("/", 1)[-1]
                if batch_id not in server.batches:
                    return self._reply(404, {"error": "not found"})
                with server._lock:
                    server.archived.append(batch_id)
                self._reply(204)

        return Handler
