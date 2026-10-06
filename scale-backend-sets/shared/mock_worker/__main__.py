"""Run one mock worker as an HTTP server, optionally pushing heartbeats.

    python -m shared.mock_worker --id w1 --port 9001 --latency 0.2 \
        --heartbeat-url http://127.0.0.1:8000/workers/heartbeat --interval 1

Control it while it runs:
    curl -X POST localhost:9001/admin/slow?factor=20
    curl -X POST localhost:9001/admin/silent
    curl -X POST localhost:9001/admin/kill        # the process exits
"""

from __future__ import annotations

import argparse
import threading

import httpx
import uvicorn

from .http import create_worker_app
from .worker import MockWorker


def _push_heartbeats(worker: MockWorker, url: str, interval: float, stop: threading.Event) -> None:
    with httpx.Client(timeout=2.0) as client:
        while not stop.wait(interval):
            payload = worker.heartbeat()
            if payload is None:
                continue
            try:
                client.post(url, json=payload)
            except httpx.HTTPError:
                pass  # the balancer being down must not kill the worker


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--id", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9001)
    parser.add_argument("--capacity", type=int, default=4)
    parser.add_argument("--latency", type=float, default=0.1)
    parser.add_argument("--heartbeat-url")
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args(argv)

    worker = MockWorker(args.id, capacity=args.capacity, latency_s=args.latency)
    stop = threading.Event()
    if args.heartbeat_url:
        threading.Thread(target=_push_heartbeats, args=(worker, args.heartbeat_url, args.interval, stop),
                         daemon=True).start()
    try:
        uvicorn.run(create_worker_app(worker), host=args.host, port=args.port)
    finally:
        stop.set()


if __name__ == "__main__":
    main()
