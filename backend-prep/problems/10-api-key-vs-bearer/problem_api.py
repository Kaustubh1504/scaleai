"""Mock Catalog + Orders services for problem 10. Tests and your __main__ block both use make_api()."""

from __future__ import annotations

from urllib.parse import parse_qsl

from kit import FakeClock, MockAPI, TokenIssuer, error_response

API_KEY = "cat_key_9f8e7d6c5b"
CLIENT_ID = "orders-sync"
CLIENT_SECRET = "s3cr3t_Zq81xLp0"

ITEMS = {
    "SKU-100": {"sku": "SKU-100", "name": "Bounding boxes, 1k", "price_cents": 12000},
    "SKU-200": {"sku": "SKU-200", "name": "Transcription hour", "price_cents": 4500},
    "SKU-300": {"sku": "SKU-300", "name": "RLHF comparison, 100", "price_cents": 30000},
}

ORDERS = [
    {"id": "ord_001", "customer": "acme", "sku": "SKU-100", "qty": 3},
    {"id": "ord_002", "customer": "globex", "sku": "SKU-300", "qty": 1},
    {"id": "ord_003", "customer": "acme", "sku": "SKU-200", "qty": 10},
]


def make_api(clock=None, token_ttl_s: float = 3600.0) -> MockAPI:
    clock = clock or FakeClock()
    api = MockAPI(clock=clock)
    issuer = TokenIssuer(clock, ttl_s=token_ttl_s)
    api.issuer = issuer

    # ---- Catalog service: static API key
    @api.route("GET", "/v1/items/{sku}")
    def get_item(req, sku):
        if req.header("x-api-key") != API_KEY:
            return error_response(401, "missing or invalid X-API-Key")
        if sku not in ITEMS:
            return error_response(404, f"no item {sku}")
        return ITEMS[sku]

    # ---- Orders service: OAuth2 client credentials, form-encoded
    @api.route("POST", "/oauth/token")
    def token(req):
        ctype = (req.header("content-type") or "").split(";")[0].strip()
        if ctype != "application/x-www-form-urlencoded":
            return 400, {"error": "invalid_request", "error_description": "body must be form-encoded"}
        form = dict(parse_qsl(req.body.decode()))
        if form.get("grant_type") != "client_credentials":
            return 400, {"error": "unsupported_grant_type"}
        if form.get("client_id") != CLIENT_ID or form.get("client_secret") != CLIENT_SECRET:
            return 401, {"error": "invalid_client"}
        return issuer.issue()

    @api.route("GET", "/v1/orders")
    def list_orders(req):
        if not issuer.valid(req.header("authorization")):
            return error_response(401, "missing, invalid or expired bearer token")
        return {"orders": ORDERS}

    return api
