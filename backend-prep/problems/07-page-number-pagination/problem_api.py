"""Mock Catalog API for problem 07. Tests and your __main__ block both use make_api()."""

from __future__ import annotations

from kit import MockAPI, error_response

API_KEY = "key_live_123"
MAX_PER_PAGE = 100


def make_products(n: int) -> list[dict]:
    cats = ("image", "text", "audio", "video")
    return [{"id": f"prd_{i:04d}", "name": f"Labeling pack {i}", "category": cats[i % 4], "price_cents": 500 + 25 * i}
            for i in range(1, n + 1)]


def make_api(n_products: int = 47, *, extra_empty_page: bool = False, empty_from_page: int | None = None,
             clock=None) -> MockAPI:
    """
    n_products       : how many products the API holds.
    extra_empty_page : the server over-counts: total_pages is one too high, so the
                       last page it advertises comes back with "data": [].
    empty_from_page  : from this page (1-based) on, "data" is [] even though
                       total_pages says there is more (a buggy/inconsistent backend).
    """
    api = MockAPI(clock=clock)
    products = make_products(n_products)
    api.products = products

    @api.route("GET", "/v1/products")
    def list_products(req):
        if req.header("x-api-key") != API_KEY:
            return error_response(401, "missing or invalid X-API-Key")
        try:
            page = int(req.params.get("page", "1"))
            per_page = int(req.params.get("per_page", "20"))
        except ValueError:
            return error_response(400, "page and per_page must be integers")
        if page < 1:
            return error_response(400, "page must be >= 1")
        if not 1 <= per_page <= MAX_PER_PAGE:
            return error_response(400, f"per_page must be between 1 and {MAX_PER_PAGE}")
        total_pages = -(-len(products) // per_page)  # 0 for an empty collection
        if extra_empty_page:
            total_pages += 1
        start = (page - 1) * per_page
        data = products[start:start + per_page]
        if empty_from_page is not None and page >= empty_from_page:
            data = []
        return {"data": data, "page": page, "per_page": per_page,
                "total": len(products), "total_pages": total_pages}

    return api
