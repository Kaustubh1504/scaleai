"""A webhook endpoint that records deliveries and fails on demand.

    receiver = WebhookReceiver(secret="whsec_test")
    receiver.script_event("evt_1", [500, 500, 200])   # fail twice, then accept
    receiver.script([503, "timeout"])                 # the next two requests (any event)
    client = httpx.Client(transport=receiver.transport())
    ...
    receiver.accepted_event_ids()  -> ["evt_1", ...]

Scripted responses: an int status, ``"timeout"`` (the client sees
``httpx.ReadTimeout``; the request still counts as received, like a server that
processed it but was too slow to answer), ``"429:<seconds>"`` (429 with a
Retry-After header) or ``"drop"`` (connection reset before anything is
processed). Per-event scripts take precedence over the global script; when both
are exhausted the receiver answers ``default_status``.

Signatures: if ``secret`` is set, each request's ``X-Webhook-Signature`` header
(``t=<unix ts>,v1=<hex HMAC-SHA256 of "<t>.<raw body>">``) is verified and the
result stored on the delivery. Use ``sign()`` to produce the header.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from collections import deque
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..fake_clock import Clock, RealClock, aelapse

SIGNATURE_HEADER = "X-Webhook-Signature"


def sign(secret: str, body: bytes, timestamp: int) -> str:
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def verify_signature(secret: str, body: bytes, header: str | None, *, now: float | None = None,
                     tolerance_s: float = 300.0) -> bool:
    if not header:
        return False
    try:
        parts = dict(item.split("=", 1) for item in header.split(","))
        timestamp = int(parts["t"])
        expected = sign(secret, body, timestamp).split("v1=", 1)[1]
    except (KeyError, ValueError):
        return False
    if now is not None and abs(now - timestamp) > tolerance_s:
        return False
    return hmac.compare_digest(expected, parts.get("v1", ""))


@dataclass
class Delivery:
    n: int
    method: str
    path: str
    headers: dict[str, str]
    body: bytes
    event_id: str | None
    received_at: float
    response: str  # "200", "500", "timeout", "429:5", ...
    signature_valid: bool | None

    @property
    def json(self) -> Any:
        try:
            return json.loads(self.body)
        except ValueError:
            return None

    @property
    def accepted(self) -> bool:
        return self.response.isdigit() and 200 <= int(self.response) < 300


class WebhookReceiver:
    def __init__(self, *, secret: str | None = None, clock: Clock | None = None, default_status: int = 200,
                 event_id_field: str = "id", event_id_header: str = "X-Event-Id"):
        self.secret = secret
        self.clock = clock or RealClock()
        self.default_status = default_status
        self.event_id_field = event_id_field
        self.event_id_header = event_id_header
        self.deliveries: list[Delivery] = []
        self._global: deque = deque()
        self._per_event: dict[str, deque] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------- scripting

    def script(self, responses: list[int | str]) -> None:
        """Responses for the next requests, whatever event they carry."""
        with self._lock:
            self._global.extend(str(r) for r in responses)

    def script_event(self, event_id: str, responses: list[int | str]) -> None:
        """Responses for successive deliveries of one event."""
        with self._lock:
            self._per_event.setdefault(event_id, deque()).extend(str(r) for r in responses)

    def fail_always(self, status: int = 500) -> None:
        self.default_status = status

    def reset(self) -> None:
        with self._lock:
            self.deliveries.clear()
            self._global.clear()
            self._per_event.clear()

    # ------------------------------------------------------------- queries

    def accepted_event_ids(self) -> list[str]:
        return [d.event_id for d in self.deliveries if d.accepted and d.event_id is not None]

    def attempts_for(self, event_id: str) -> list[Delivery]:
        return [d for d in self.deliveries if d.event_id == event_id]

    # ------------------------------------------------------------- handling

    def _event_id(self, headers: dict[str, str], body: bytes) -> str | None:
        lowered = {k.lower(): v for k, v in headers.items()}
        if self.event_id_header.lower() in lowered:
            return lowered[self.event_id_header.lower()]
        try:
            data = json.loads(body)
        except ValueError:
            return None
        value = data.get(self.event_id_field) if isinstance(data, dict) else None
        return str(value) if value is not None else None

    def handle(self, method: str, path: str, headers: dict[str, str], body: bytes) -> tuple[str, int, dict]:
        """Record a request. Returns (outcome, status, response headers)."""
        event_id = self._event_id(headers, body)
        with self._lock:
            queue = self._per_event.get(event_id) if event_id is not None else None
            if queue:
                outcome = queue.popleft()
            elif self._global:
                outcome = self._global.popleft()
            else:
                outcome = str(self.default_status)
            if outcome == "drop":
                return outcome, 0, {}
            signature_valid = None
            if self.secret is not None:
                header = next((v for k, v in headers.items() if k.lower() == SIGNATURE_HEADER.lower()), None)
                signature_valid = verify_signature(self.secret, body, header, now=self.clock.time())
            self.deliveries.append(Delivery(len(self.deliveries) + 1, method, path, dict(headers), body,
                                            event_id, self.clock.time(), outcome, signature_valid))
        if outcome == "timeout":
            return outcome, 0, {}
        if outcome.startswith("429"):
            retry_after = outcome.partition(":")[2] or "1"
            return outcome, 429, {"Retry-After": retry_after}
        return outcome, int(outcome), {}

    def transport(self) -> httpx.MockTransport:
        """An httpx transport that delivers straight into this receiver (sync and async clients)."""

        def handler(request: httpx.Request) -> httpx.Response:
            outcome, status, headers = self.handle(request.method, request.url.path,
                                                   dict(request.headers), request.content)
            if outcome == "drop":
                raise httpx.ConnectError("connection reset", request=request)
            if outcome == "timeout":
                raise httpx.ReadTimeout("receiver did not answer in time", request=request)
            return httpx.Response(status, headers=headers, json={"received": 200 <= status < 300})

        return httpx.MockTransport(handler)

    def app(self) -> FastAPI:
        """A real HTTP server that accepts POSTs on any path."""
        app = FastAPI(title="Mock webhook receiver")

        @app.get("/_deliveries")
        def deliveries() -> list[dict]:
            return [{"n": d.n, "path": d.path, "event_id": d.event_id, "response": d.response,
                     "signature_valid": d.signature_valid, "received_at": d.received_at, "body": d.json}
                    for d in self.deliveries]

        @app.post("/{path:path}")
        async def receive(path: str, request: Request):
            outcome, status, headers = self.handle("POST", "/" + path, dict(request.headers), await request.body())
            if outcome in ("timeout", "drop"):
                await aelapse(self.clock, 60)
                status = 504
            return JSONResponse({"received": 200 <= status < 300}, status_code=status, headers=headers)

        return app
