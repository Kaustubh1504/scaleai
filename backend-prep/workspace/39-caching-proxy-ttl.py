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


def create_app(upstream: httpx.Client, clock, ttl_s: float = 30, negative_ttl_s: float = 5) -> FastAPI:
    cache: dict[str, Entry] = {}
    lock = threading.Lock()  # def-handlers run in a thread pool
    app = FastAPI(title="Catalog cache")
    
    def reply(status: int, body, source: str) -> JSONResponse:
        if status == 404:
            body = {"detail": "product not found"}
        return JSONResponse(body, status_code=status, headers={"X-Cache": source})

    @app.get("/products/{product_id}")
    def get_product(product_id: str) -> Response:
        entry = cache.get(product_id)
        if entry:
            status, body, stored_at = entry
            if clock.time() < stored_at + (ttl_s if status==200 else negative_ttl_s):
                return reply(status, body, "HIT")
        
        try:
            resp = upstream.get(f"/v1/products/{product_id}")
            
            if resp.status_code in (200, 404):
                body = resp.json() if resp.status_code == 200 else None
                cache[product_id] = (resp.status_code, body, clock.time())
                return reply(resp.status_code, body, "MISS")
        
        except (httpx.TransportError, ValueError):
            pass
        
        if entry and entry[0] == 200:
            return reply(200, entry[1], "STALE")
        return reply(502, {"detail": "upstream unavailable"}, "MISS")
            

    @app.post("/cache/purge/{product_id}", status_code=204)
    def purge(product_id: str) -> Response:
        cache.pop(product_id, None)

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
