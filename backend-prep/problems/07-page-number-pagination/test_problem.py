import pytest

from problem_api import API_KEY, make_api


def ids(items):
    return [p["id"] for p in items]


def pages_requested(api):
    return [c.params.get("page") for c in api.calls("GET", "/v1/products")]


def test_fetches_every_product_in_order(sol):
    """Returns all 47 products, in API order"""
    api = make_api(n_products=47)
    products = sol.fetch_all_products(api.client(), API_KEY, per_page=20)
    assert ids(products) == ids(api.products), "products missing, duplicated or out of order"


def test_requests_pages_in_order_once(sol):
    """Requests pages 1, 2, 3 exactly once each, sending per_page every time"""
    api = make_api(n_products=47)
    sol.fetch_all_products(api.client(), API_KEY, per_page=20)
    assert pages_requested(api) == ["1", "2", "3"], f"expected pages 1,2,3 once each, got {pages_requested(api)}"
    assert all(c.params.get("per_page") == "20" for c in api.log), "every request must pass per_page=20"


def test_sends_api_key(sol):
    """Sends the X-API-Key header on every request"""
    api = make_api(n_products=12)
    sol.fetch_all_products(api.client(), API_KEY, per_page=5)
    assert api.log and all(c.header("x-api-key") == API_KEY for c in api.log)


def test_exact_multiple_of_per_page(sol):
    """Handles a total that divides evenly by per_page (stops at total_pages, no extra request)"""
    api = make_api(n_products=60)
    products = sol.fetch_all_products(api.client(), API_KEY, per_page=20)
    assert len(products) == 60
    assert pages_requested(api) == ["1", "2", "3"], f"page 4 does not exist; got {pages_requested(api)}"


def test_single_page(sol):
    """A catalog that fits on one page costs exactly one request"""
    api = make_api(n_products=5)
    products = sol.fetch_all_products(api.client(), API_KEY, per_page=20)
    assert ids(products) == ids(api.products)
    assert pages_requested(api) == ["1"]


def test_empty_catalog_total_pages_zero(sol):
    """An empty catalog (total_pages 0) returns [] after exactly one request"""
    api = make_api(n_products=0)
    assert sol.fetch_all_products(api.client(), API_KEY) == []
    assert pages_requested(api) == ["1"], f"total_pages is 0: one request is enough, got {pages_requested(api)}"


def test_trailing_empty_page(sol):
    """total_pages one too high: the empty last page ends the crawl cleanly"""
    api = make_api(n_products=40, extra_empty_page=True)  # says 3 pages, page 3 is empty
    products = sol.fetch_all_products(api.client(), API_KEY, per_page=20)
    assert ids(products) == ids(api.products)
    assert pages_requested(api) == ["1", "2", "3"], f"got {pages_requested(api)}"


def test_stops_on_early_empty_page(sol):
    """An empty page before total_pages stops the crawl without requesting the next page"""
    api = make_api(n_products=100, empty_from_page=3)  # says 5 pages, page 3 is empty
    products = sol.fetch_all_products(api.client(), API_KEY, per_page=20)
    assert ids(products) == ids(api.products[:40]), "keep what pages 1 and 2 returned"
    assert pages_requested(api) == ["1", "2", "3"], f"stop at the first empty page; got {pages_requested(api)}"


def test_error_raises_api_error(sol):
    """A 503 on page 2 raises ApiError(503) with path /v1/products"""
    api = make_api(n_products=47)
    api.script("GET /v1/products", ["pass", 503])
    with pytest.raises(sol.ApiError) as exc:
        sol.fetch_all_products(api.client(), API_KEY, per_page=20)
    assert exc.value.status == 503
    assert exc.value.path == "/v1/products"


def test_bad_key_raises_api_error(sol):
    """A wrong API key raises ApiError(401)"""
    api = make_api(n_products=5)
    with pytest.raises(sol.ApiError) as exc:
        sol.fetch_all_products(api.client(), "wrong-key")
    assert exc.value.status == 401
