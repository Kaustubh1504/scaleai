"""Fake OpenAI API for the hidden graders' fault tests (stdlib only).

Real OpenAI cannot be made to return 429 / 503 / timeouts / garbage on demand,
so fault tests point OPENAI_BASE_URL here.  Supports both
POST {base}/chat/completions and POST {base}/responses  (base = <url>/v1).

Each request's text (all message / input content) is searched for exactly one
known *marker* (a substring); the next scripted action for it is played.

Actions:
    ("json", obj)        200, assistant text = json.dumps(obj)
    ("text", str)        200, assistant text = str
    ("status", code)     error status with an Anthropic-style error body
    ("sleep", secs, act) sleep, then play act
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _text_of(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


class MockLLM:
    def __init__(self, api_key: str, script=None, default=None, delay: float = 0.0, allow_multi: bool = False):
        self.api_key = api_key
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.default = default or (lambda text: ("json", {"category": "other"}))
        self.delay = delay
        self.allow_multi = allow_multi
        self.calls: list[dict] = []
        self.per_marker: dict[str, int] = defaultdict(int)
        self.in_flight = 0
        self.peak = 0
        self.lock = threading.Lock()
        self._server = None

    # -- scripting ---------------------------------------------------------
    def set_script(self, script):
        with self.lock:
            self.script = {k: list(v) for k, v in script.items()}

    def reset_counts(self):
        with self.lock:
            self.calls.clear()
            self.per_marker.clear()
            self.peak = 0

    def count(self, marker=None) -> int:
        with self.lock:
            return len(self.calls) if marker is None else self.per_marker.get(marker, 0)

    def _action_for(self, text: str):
        with self.lock:
            found = [m for m in self.script if m in text]
            # drop markers that are substrings of another found marker
            found = [m for m in found if not any(m != o and m in o for o in found)]
            if len(found) > 1 and not self.allow_multi:
                return None, ("status", 400)
            marker = found[0] if found else None
            if marker is None:
                return None, self.default(text)
            idx = self.per_marker[marker]
            seq = self.script[marker]
            act = seq[min(idx, len(seq) - 1)]
            return marker, act

    # -- server ------------------------------------------------------------
    def start(self):
        mock = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):  # silence
                pass

            def _send(self, code, obj):
                body = json.dumps(obj).encode()
                try:
                    self.send_response(code)
                    self.send_header("content-type", "application/json")
                    self.send_header("content-length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_POST(self):
                length = int(self.headers.get("content-length") or 0)
                raw = self.rfile.read(length)
                path = self.path.split("?")[0].rstrip("/")
                if path not in ("/v1/chat/completions", "/v1/responses"):
                    return self._send(404, {"error": {"type": "invalid_request_error", "message": "unknown path"}})
                try:
                    body = json.loads(raw)
                    if path.endswith("/chat/completions"):
                        parts = [_text_of(m.get("content")) for m in body["messages"]]
                    else:
                        inp = body["input"]
                        parts = [_text_of(body.get("instructions"))]
                        parts += [inp] if isinstance(inp, str) else [_text_of(m.get("content")) for m in inp]
                    text = "\n".join(parts)
                except Exception:
                    return self._send(400, {"error": {"type": "invalid_request_error", "message": "bad body"}})
                marker, act = mock._action_for(text)
                if self.headers.get("authorization") != f"Bearer {mock.api_key}":
                    marker, act = None, ("status", 401)
                with mock.lock:
                    mock.in_flight += 1
                    mock.peak = max(mock.peak, mock.in_flight)
                    mock.calls.append({"marker": marker, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body, "text": text})
                    if marker is not None:
                        mock.per_marker[marker] += 1
                try:
                    if mock.delay:
                        time.sleep(mock.delay)
                    while act[0] == "sleep":
                        time.sleep(act[1])
                        act = act[2]
                    kind = act[0]
                    if kind == "status":
                        etype = {429: "rate_limit_exceeded", 401: "invalid_api_key", 400: "invalid_request_error"}.get(
                            act[1], "server_error")
                        return self._send(act[1], {"error": {"type": etype, "code": etype, "message": "mock"}})
                    out = json.dumps(act[1]) if kind == "json" else act[1]
                    model = body.get("model", "mock")
                    if path.endswith("/chat/completions"):
                        return self._send(200, {
                            "id": "chatcmpl-mock", "object": "chat.completion", "created": int(time.time()),
                            "model": model,
                            "choices": [{"index": 0, "finish_reason": "stop", "logprobs": None,
                                         "message": {"role": "assistant", "content": out, "refusal": None}}],
                            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                        })
                    return self._send(200, {
                        "id": "resp_mock", "object": "response", "created_at": int(time.time()),
                        "status": "completed", "model": model, "error": None, "incomplete_details": None,
                        "output": [{"type": "message", "id": "msg_mock", "status": "completed", "role": "assistant",
                                    "content": [{"type": "output_text", "text": out, "annotations": []}]}],
                        "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
                    })
                finally:
                    with mock.lock:
                        mock.in_flight -= 1

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        return self

    @property
    def url(self) -> str:
        """Value for OPENAI_BASE_URL (includes /v1, like the real default)."""
        return f"http://127.0.0.1:{self._server.server_address[1]}/v1"

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
