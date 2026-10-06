"""HTTP faces of ``MockWorker``.

``worker_transport({"http://w1": w1, "http://w2": w2})`` returns an
``httpx.MockTransport`` so code that talks to workers over HTTP can be tested
without sockets. Dead workers raise ``httpx.ConnectError``; silent ones raise
``httpx.ReadTimeout``, exactly what a real client would see.

Worker HTTP API
---------------
POST /process  {"task": ...}  -> 200 {"result": ...}
                                 503 {"error": "overloaded"}
                                 500 {"error": "task failed: ..."}
GET  /health                  -> 200 {"worker_id", "state", "in_flight", "capacity"}
"""

from __future__ import annotations

import json
import os
import threading

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from ..fake_clock import aelapse
from .worker import (
    MockWorker,
    TaskFailedError,
    WorkerOverloadedError,
    WorkerState,
    WorkerTimeoutError,
    WorkerUnreachableError,
)


def _health(worker: MockWorker) -> dict:
    return {"worker_id": worker.worker_id, "state": worker.state.value,
            "in_flight": worker.in_flight, "capacity": worker.capacity}


def worker_transport(workers: dict[str, MockWorker]) -> httpx.MockTransport:
    by_host = {httpx.URL(url).host: w for url, w in workers.items()}

    def handle(request: httpx.Request) -> httpx.Response:
        worker = by_host.get(request.url.host)
        if worker is None or worker.state is WorkerState.DEAD:
            raise httpx.ConnectError("connection refused", request=request)
        if request.url.path == "/health":
            if worker.state is WorkerState.SILENT:
                raise httpx.ReadTimeout("no response", request=request)
            return httpx.Response(200, json=_health(worker))
        if request.method == "POST" and request.url.path == "/process":
            timeout = request.extensions.get("timeout", {}).get("read")
            task = json.loads(request.content or b"{}").get("task")
            try:
                return httpx.Response(200, json={"result": worker.process(task, timeout=timeout)})
            except WorkerOverloadedError:
                return httpx.Response(503, json={"error": "overloaded"})
            except TaskFailedError as exc:
                return httpx.Response(500, json={"error": str(exc)})
            except WorkerTimeoutError as exc:
                raise httpx.ReadTimeout(str(exc), request=request) from exc
            except WorkerUnreachableError as exc:
                raise httpx.RemoteProtocolError(str(exc), request=request) from exc
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handle)


def create_worker_app(worker: MockWorker) -> FastAPI:
    """A real HTTP server for one worker (see ``python -m shared.mock_worker``)."""
    app = FastAPI(title=f"Mock worker {worker.worker_id}")

    @app.get("/health")
    async def health():
        if worker.state is WorkerState.SILENT:
            await aelapse(worker.clock, worker.hang_s)
        return _health(worker)

    @app.post("/process")
    async def process(body: dict):
        try:
            return {"result": await worker.aprocess(body.get("task"))}
        except WorkerOverloadedError:
            return JSONResponse({"error": "overloaded"}, status_code=503)
        except TaskFailedError as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)
        except (WorkerTimeoutError, WorkerUnreachableError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=504)

    @app.post("/admin/{action}")
    def admin(action: str, factor: float = 10.0):
        actions = {"slow": lambda: worker.slow(factor), "silent": worker.go_silent,
                   "revive": worker.revive, "crash_on_next": worker.crash_on_next}
        if action == "kill":
            # A killed process really disappears: exit shortly after replying.
            threading.Timer(0.1, lambda: os._exit(1)).start()
            return {"state": "dying"}
        if action not in actions:
            return JSONResponse({"error": f"unknown action {action}"}, status_code=404)
        actions[action]()
        return _health(worker)

    return app
