"""Mock upstream Catalog API for problem 39. Tests and your __main__ block both use make_api()."""

from __future__ import annotations

from kit import MockAPI, error_response

PRODUCTS = {
    "p1": {"id": "p1", "name": "Bounding-box QA pack", "price_cents": 1200, "stock": 14},
    "p2": {"id": "p2", "name": "Transcription minutes", "price_cents": 45, "stock": 9000},
    "p3": {"id": "p3", "name": "RLHF comparison set", "price_cents": 30000, "stock": 2},
}


def make_api(clock=None, latency_s: float = 0.0) -> MockAPI:
    """
    The upstream: GET /v1/products/{product_id} -> 200 product JSON, or 404.
    ``api.products`` is the live catalog: tests edit it to simulate upstream changes.
    """
    api = MockAPI(clock=clock, latency_s=latency_s)
    api.products = {pid: dict(p) for pid, p in PRODUCTS.items()}

    @api.route("GET", "/v1/products/{product_id}")
    def get_product(req, product_id):
        product = api.products.get(product_id)
        if product is None:
            return error_response(404, f"no product {product_id}")
        return dict(product)

    return api
