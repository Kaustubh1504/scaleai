"""39. Caching proxy with TTL and stale fallback

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import threading
from dataclasses import dataclass
from typing import Any
import httpx
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

NOT_FOUND = {"detail": "product not found"}
UNAVAILABLE = {"detail": "upstream unavailable"}


@dataclass(frozen=True)
class Entry:
    status: int          # 200 (a product) or 404 (a not-found)
    body: Any            # the product JSON; None for a not-found
    stored_at: float


def create_app(upstream: httpx.Client, clock, ttl_s: float = 30, negative_ttl_s: float = 5) -> FastAPI:
    cache: dict[str, Entry] = {}
    lock = threading.Lock()  # def-handlers run in a thread pool
    app = FastAPI(title="Catalog cache")

    @app.get("/products/{product_id}")
    def get_product(product_id: str) -> Response:
        raise NotImplementedError

    @app.post("/cache/purge/{product_id}", status_code=204)
    def purge(product_id: str) -> Response:
        raise NotImplementedError

    return app


if __name__ == "__main__":
    import warnings

    warnings.filterwarnings("ignore", message="Using `httpx`")  # starlette TestClient notice
    from fastapi.testclient import TestClient

    from kit import FakeClock
    from problem_api import make_api

    api, clock = make_api(), FakeClock()
    c = TestClient(create_app(api.client(), clock, ttl_s=30))

    def show(label: str, resp) -> None:
        print(f"{label:<28} {resp.status_code} {resp.headers.get('x-cache'):<5} {resp.json()}"
              f"  (upstream calls: {len(api.log)})")

    show("first read", c.get("/products/p1"))
    clock.advance(10)
    show("10s later", c.get("/products/p1"))
    clock.advance(20)
    api.script("GET /v1/products/p1", [503])
    show("30s later, upstream 503", c.get("/products/p1"))
    show("upstream back", c.get("/products/p1"))
    show("unknown id", c.get("/products/p9"))
    show("unknown id again", c.get("/products/p9"))
