"""Fake customer callback endpoint for the 07 grader (stdlib only).

    POST <url>   JSON body; X-Signature must be "sha256=" + hex HMAC-SHA256(secret, raw body), else 401

Actions are scripted per task_id in the body (call k plays action k, the last
one repeats). Unscripted task_ids get `default`.

Actions:
    ("status", code)     respond with that status
    ("sleep", secs, act) sleep, then play act
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MockCallbacks:
    def __init__(self, secret: str, script=None, default=("status", 200), delay: float = 0.0):
        self.secret = secret
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.default = default
        self.delay = delay
        self.calls: list[dict] = []
        self.per_task: dict[str, int] = defaultdict(int)
        self.in_flight = 0
        self.peak = 0
        self.lock = threading.Lock()
        self._server = None

    def reset_counts(self):
        with self.lock:
            self.calls.clear()
            self.per_task.clear()
            self.peak = 0

    def count(self, task_id=None) -> int:
        with self.lock:
            return len(self.calls) if task_id is None else self.per_task.get(task_id, 0)

    def start(self):
        mock = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _send(self, code):
                body = json.dumps({"status": code}).encode()
                try:
                    self.send_response(code)
                    self.send_header("content-type", "application/json")
                    self.send_header("content-length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get("content-length") or 0))
                try:
                    body = json.loads(raw)
                    tid = body.get("task_id") if isinstance(body, dict) else None
                except ValueError:
                    body, tid = None, None
                want = "sha256=" + hmac.new(mock.secret.encode(), raw, hashlib.sha256).hexdigest()
                signed = hmac.compare_digest(self.headers.get("x-signature", ""), want)
                with mock.lock:
                    mock.in_flight += 1
                    mock.peak = max(mock.peak, mock.in_flight)
                    mock.calls.append({"task_id": tid, "body": body, "raw": raw, "signed": signed,
                                       "headers": {k.lower(): v for k, v in self.headers.items()}})
                    idx = mock.per_task[tid]
                    mock.per_task[tid] += 1
                    seq = mock.script.get(tid)
                    act = seq[min(idx, len(seq) - 1)] if seq else mock.default
                try:
                    if not signed:
                        return self._send(401)
                    if body is None or tid is None:
                        return self._send(400)
                    if mock.delay:
                        time.sleep(mock.delay)
                    while act[0] == "sleep":
                        time.sleep(act[1])
                        act = act[2]
                    return self._send(act[1])
                finally:
                    with mock.lock:
                        mock.in_flight -= 1

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        return self

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}/hooks/labels"

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
