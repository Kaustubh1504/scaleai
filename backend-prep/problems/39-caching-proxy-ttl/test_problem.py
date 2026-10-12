import warnings

import pytest

warnings.filterwarnings("ignore", message="Using `httpx`")  # starlette TestClient notice
from fastapi.testclient import TestClient  # noqa: E402

from problem_api import PRODUCTS, make_api  # noqa: E402

P1 = "/v1/products/p1"


@pytest.fixture
def api():
    return make_api()


@pytest.fixture
def proxy(sol, api, clock):
    return TestClient(sol.create_app(api.client(), clock, ttl_s=30))


def get(c, pid, status, cache):
    resp = c.get(f"/products/{pid}")
    assert resp.status_code == status, f"GET /products/{pid}: expected {status}, got {resp.status_code}: {resp.text[:200]}"
    assert resp.headers.get("x-cache") == cache, \
        f"GET /products/{pid}: expected X-Cache {cache}, got {resp.headers.get('x-cache')!r}"
    return resp.json()


def upstream_calls(api, path=P1):
    return len(api.calls("GET", path))


def test_miss_then_hit(proxy, api, clock):
    """First read is a MISS with the upstream body; a repeat within the TTL is a HIT with no upstream call"""
    assert get(proxy, "p1", 200, "MISS") == PRODUCTS["p1"]
    clock.advance(10)
    assert get(proxy, "p1", 200, "HIT") == PRODUCTS["p1"]
    assert upstream_calls(api) == 1, f"a HIT must not call upstream; made {upstream_calls(api)} calls"


def test_ttl_boundary_and_refresh(proxy, api, clock):
    """Fresh while now < stored_at + 30; at exactly +30 it refetches, picks up changes and is fresh again"""
    t0 = clock.time()
    get(proxy, "p1", 200, "MISS")
    api.products["p1"]["price_cents"] = 999
    clock.set(t0 + 29.9)
    assert get(proxy, "p1", 200, "HIT")["price_cents"] == 1200, "still fresh: serve the cached copy"
    clock.set(t0 + 30)
    assert get(proxy, "p1", 200, "MISS")["price_cents"] == 999, "expired at exactly stored_at + ttl"
    assert upstream_calls(api) == 2
    clock.advance(29)
    get(proxy, "p1", 200, "HIT")
    assert upstream_calls(api) == 2, "the refreshed copy must get a new stored_at"


def test_ids_cached_separately_and_ttl_param(sol, api, clock):
    """Each id has its own entry; ttl_s is honoured"""
    c = TestClient(sol.create_app(api.client(), clock, ttl_s=10))
    get(c, "p1", 200, "MISS")
    clock.advance(4)
    assert get(c, "p2", 200, "MISS") == PRODUCTS["p2"], "p2 was never fetched"
    get(c, "p1", 200, "HIT")
    clock.advance(6)  # p1 at +10 (expired), p2 at +6 (fresh)
    get(c, "p1", 200, "MISS")
    get(c, "p2", 200, "HIT")
    assert upstream_calls(api, P1) == 2 and upstream_calls(api, "/v1/products/p2") == 1


def test_not_found_is_cached_briefly(proxy, api, clock):
    """An upstream 404 is a 404 cached for negative_ttl_s (5s), then the upstream is asked again"""
    path = "/v1/products/p9"
    t0 = clock.time()
    assert get(proxy, "p9", 404, "MISS") == {"detail": "product not found"}
    clock.set(t0 + 4.9)
    assert get(proxy, "p9", 404, "HIT") == {"detail": "product not found"}
    assert upstream_calls(api, path) == 1, "a cached 404 must not call upstream"
    api.products["p9"] = {"id": "p9", "name": "New", "price_cents": 1, "stock": 1}
    clock.set(t0 + 5)
    assert get(proxy, "p9", 200, "MISS")["name"] == "New", "the not-found expires after 5s"
    assert upstream_calls(api, path) == 2
    clock.advance(20)
    get(proxy, "p9", 200, "HIT")  # now a product: the 30s TTL applies


def test_fresh_entry_shields_upstream_outage(proxy, api, clock):
    """While an entry is fresh, an upstream outage is invisible (HIT, upstream not called)"""
    get(proxy, "p1", 200, "MISS")
    api.script("GET " + P1, [503, 503])
    clock.advance(15)
    get(proxy, "p1", 200, "HIT")
    assert upstream_calls(api) == 1


def test_5xx_serves_stale_or_502(proxy, api, clock):
    """Upstream 5xx: an expired product is served STALE; with nothing cached it is 502"""
    get(proxy, "p1", 200, "MISS")
    clock.advance(31)
    api.products["p1"]["stock"] = 0
    api.script("GET " + P1, [503])
    assert get(proxy, "p1", 200, "STALE") == PRODUCTS["p1"], "serve the last good copy, unchanged"
    assert upstream_calls(api) == 2, "an expired entry must try upstream before going stale"

    api.script("GET /v1/products/p2", [500])
    assert get(proxy, "p2", 502, "MISS") == {"detail": "upstream unavailable"}


def test_transport_errors_and_other_statuses(proxy, api, clock):
    """Timeouts, connection errors, 429 and other unexpected statuses are failures too (STALE or 502)"""
    get(proxy, "p1", 200, "MISS")
    clock.advance(30)
    for fault in ("timeout", "connect", "429:1", 400):
        api.script("GET " + P1, [fault])
        assert get(proxy, "p1", 200, "STALE") == PRODUCTS["p1"], f"upstream fault {fault!r} should serve stale"
    for fault in ("timeout", "connect"):
        api.script("GET /v1/products/p3", [fault])
        get(proxy, "p3", 502, "MISS")


def test_malformed_body_is_a_failure_and_not_cached(proxy, api, clock):
    """A 200 with a non-JSON body counts as a failure: 502 (or STALE) and nothing is cached"""
    path = "/v1/products/p2"
    api.script("GET " + path, ["malformed"])
    get(proxy, "p2", 502, "MISS")
    assert get(proxy, "p2", 200, "MISS") == PRODUCTS["p2"], "the broken body must not have been cached"
    assert upstream_calls(api, path) == 2


def test_stale_does_not_refresh(proxy, api, clock):
    """Serving STALE keeps the old stored_at: the next request tries upstream again"""
    get(proxy, "p1", 200, "MISS")
    clock.advance(40)
    api.script("GET " + P1, [503, 503])
    get(proxy, "p1", 200, "STALE")
    get(proxy, "p1", 200, "STALE")
    api.products["p1"]["name"] = "Renamed"
    assert get(proxy, "p1", 200, "MISS")["name"] == "Renamed", "upstream recovered: fetch and re-cache"
    get(proxy, "p1", 200, "HIT")
    assert upstream_calls(api) == 4


def test_expired_not_found_is_not_a_stale_copy(proxy, api, clock):
    """A not-found is never served stale: expired 404 + upstream failure is 502"""
    get(proxy, "p9", 404, "MISS")
    clock.advance(5)
    api.script("GET /v1/products/p9", [503])
    get(proxy, "p9", 502, "MISS")


def test_purge(proxy, api, clock):
    """POST /cache/purge/{id} is 204 and forces the next read upstream; purging an unknown id is 204"""
    get(proxy, "p1", 200, "MISS")
    resp = proxy.post("/cache/purge/p1")
    assert resp.status_code == 204, f"expected 204, got {resp.status_code}"
    get(proxy, "p1", 200, "MISS")
    assert upstream_calls(api) == 2

    get(proxy, "p9", 404, "MISS")
    assert proxy.post("/cache/purge/p9").status_code == 204
    get(proxy, "p9", 404, "MISS")
    assert proxy.post("/cache/purge/never-seen").status_code == 204
