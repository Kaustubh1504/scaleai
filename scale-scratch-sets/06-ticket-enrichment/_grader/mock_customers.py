"""Fake Customer API for the 06 grader (stdlib only).

    GET /customers/{customer_id}   header X-Api-Key must match, else 401

Each customer_id has a scripted list of actions; call k plays action k (the last
one repeats). Unscripted ids go to `default(customer_id)`.

Actions:
    ("json", obj)        200 with obj as the JSON body
    ("text", str)        200 with a non-JSON body
    ("status", code)     that status with a small JSON error body
    ("sleep", secs, act) sleep, then play act
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote


class MockCustomers:
    def __init__(self, api_key: str, script=None, default=None, delay: float = 0.0):
        self.api_key = api_key
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.default = default or (lambda cid: ("status", 404))
        self.delay = delay
        self.calls: list[dict] = []
        self.per_id: dict[str, int] = defaultdict(int)
        self.in_flight = 0
        self.peak = 0
        self.lock = threading.Lock()
        self._server = None

    def reset_counts(self):
        with self.lock:
            self.calls.clear()
            self.per_id.clear()
            self.peak = 0

    def count(self, cid=None) -> int:
        with self.lock:
            return len(self.calls) if cid is None else self.per_id.get(cid, 0)

    def _action_for(self, cid: str):
        with self.lock:
            idx = self.per_id[cid]
            self.per_id[cid] += 1
            seq = self.script.get(cid)
            if seq is None:
                return self.default(cid)
            return seq[min(idx, len(seq) - 1)]

    def start(self):
        mock = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _send(self, code, body: bytes, ctype="application/json"):
                try:
                    self.send_response(code)
                    self.send_header("content-type", ctype)
                    self.send_header("content-length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_GET(self):
                path = self.path.split("?")[0]
                if not path.startswith("/customers/") or path.count("/") != 2:
                    return self._send(404, b'{"error": "unknown path"}')
                cid = unquote(path[len("/customers/"):])
                with mock.lock:
                    mock.in_flight += 1
                    mock.peak = max(mock.peak, mock.in_flight)
                    mock.calls.append({"id": cid, "headers": {k.lower(): v for k, v in self.headers.items()}})
                try:
                    if self.headers.get("x-api-key") != mock.api_key:
                        with mock.lock:
                            mock.per_id[cid] += 1
                        return self._send(401, b'{"error": "bad api key"}')
                    act = mock._action_for(cid)
                    if mock.delay:
                        time.sleep(mock.delay)
                    while act[0] == "sleep":
                        time.sleep(act[1])
                        act = act[2]
                    if act[0] == "status":
                        return self._send(act[1], json.dumps({"error": f"mock {act[1]}"}).encode())
                    if act[0] == "text":
                        return self._send(200, act[1].encode(), "text/html")
                    return self._send(200, json.dumps(act[1]).encode())
                finally:
                    with mock.lock:
                        mock.in_flight -= 1

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        return self

    @property
    def url(self) -> str:
        """Value for CUSTOMER_API_URL (no trailing slash)."""
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
