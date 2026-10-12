import copy
from collections import Counter

import pytest

from problem_api import DANGLING_USER_IDS, make_api, make_orders


def test_fetches_each_user_once(sol):
    """500 orders make exactly one request per distinct user_id"""
    api = make_api()
    orders = make_orders()
    sol.enrich_orders(api.client(), orders)
    distinct = {o["user_id"] for o in orders}
    per_path = Counter(c.path for c in api.log)
    assert len(api.log) == len(distinct), f"expected {len(distinct)} requests (one per user), made {len(api.log)}"
    assert max(per_path.values()) == 1, f"some users were fetched more than once: {per_path.most_common(3)}"


def test_enriches_every_order_in_order(sol):
    """Each order keeps its fields, gains the right "user", and the list order is unchanged"""
    api = make_api()
    orders = make_orders()
    enriched = sol.enrich_orders(api.client(), orders)
    assert [o["id"] for o in enriched] == [o["id"] for o in orders], "keep the input order"
    for src, out in zip(orders, enriched):
        assert {k: out[k] for k in src} == src, f"{src['id']}: original fields must be kept"
        if src["user_id"] not in DANGLING_USER_IDS:
            assert out["user"] == api.users[src["user_id"]], f"{src['id']}: wrong user attached"


def test_deleted_user_is_none_and_cached(sol):
    """Orders for a 404 user get "user": None, and that user is requested only once"""
    api = make_api()
    orders = make_orders()
    enriched = sol.enrich_orders(api.client(), orders)
    missing = [o for o in enriched if o["user_id"] in DANGLING_USER_IDS]
    assert len(missing) == 10, "make_orders() has 10 orders pointing at deleted users"
    assert all(o["user"] is None for o in missing), "a 404 user should be attached as None"
    for uid in DANGLING_USER_IDS:
        n = len(api.calls("GET", f"/v1/users/{uid}"))
        assert n == 1, f"{uid} 404s for 5 orders but should be requested once (negative caching), was {n}"


def test_does_not_mutate_input(sol):
    """enrich_orders leaves the input list and its dicts untouched"""
    api = make_api()
    orders = make_orders(n=50)
    before = copy.deepcopy(orders)
    sol.enrich_orders(api.client(), orders)
    assert orders == before, "build new dicts ({**order, 'user': ...}) instead of writing into the input"


def test_server_error_raises(sol):
    """A 500 for a user raises ApiError with status 500 and that user's path"""
    api = make_api()
    api.script("GET /v1/users/usr_003", [500])
    orders = [{"id": "o1", "user_id": "usr_001", "total_cents": 1},
              {"id": "o2", "user_id": "usr_003", "total_cents": 2}]
    with pytest.raises(sol.ApiError) as exc:
        sol.enrich_orders(api.client(), orders)
    assert exc.value.status == 500
    assert exc.value.path == "/v1/users/usr_003"


def test_ttl_expires_exactly_at_deadline(sol, clock):
    """An entry is a hit just before set_time + ttl and gone at exactly set_time + ttl"""
    cache = sol.TTLCache(clock, ttl_s=60)
    cache.set("a", 1)
    clock.advance(59.999)
    assert cache.get("a") == 1, "still fresh at t + 59.999"
    clock.advance(0.001)
    assert cache.get("a") is None, "expired when clock.time() >= set_time + ttl"
    assert cache.get("a", "dflt") == "dflt", "an expired key behaves like a missing key"


def test_get_missing_returns_default(sol, clock):
    """get() of an unknown key returns None or the given default"""
    cache = sol.TTLCache(clock, ttl_s=10)
    assert cache.get("nope") is None
    assert cache.get("nope", 42) == 42


def test_get_or_load_loads_once_then_reloads_after_expiry(sol, clock):
    """get_or_load calls the loader once while fresh, and again after the TTL"""
    cache = sol.TTLCache(clock, ttl_s=30)
    calls = []

    def loader():
        calls.append(clock.time())
        return f"v{len(calls)}"

    assert cache.get_or_load("k", loader) == "v1"
    clock.advance(10)
    assert cache.get_or_load("k", loader) == "v1"
    assert len(calls) == 1, "fresh value: the loader must not run again"
    clock.advance(20)
    assert cache.get_or_load("k", loader) == "v2", "expired at t + 30, so load again"
    assert len(calls) == 2


def test_get_or_load_caches_none(sol, clock):
    """A loader result of None is cached (negative caching): the loader runs once"""
    cache = sol.TTLCache(clock, ttl_s=30)
    calls = []

    def loader():
        calls.append(1)
        return None

    for _ in range(3):
        assert cache.get_or_load("ghost", loader) is None
    assert len(calls) == 1, f"loader ran {len(calls)} times: a cached None is still a hit"


def test_set_replaces_and_restarts_ttl(sol, clock):
    """Re-setting a key replaces the value and restarts its TTL"""
    cache = sol.TTLCache(clock, ttl_s=10)
    cache.set("a", 1)
    clock.advance(8)
    cache.set("a", 2)
    clock.advance(8)
    assert cache.get("a") == 2, "the second set() at t+8 lives until t+18"
    clock.advance(2)
    assert cache.get("a") is None


def test_lru_eviction(sol, clock):
    """With max_items=2, a get() hit protects a key: set a, set b, get a, set c evicts b"""
    cache = sol.TTLCache(clock, ttl_s=100, max_items=2)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    cache.set("c", 3)
    assert cache.get("b") is None, "b was least recently used and should be evicted"
    assert cache.get("a") == 1, "a was used more recently than b"
    assert cache.get("c") == 3


def test_overwrite_does_not_evict_and_unbounded_by_default(sol, clock):
    """Re-setting an existing key never evicts; max_items=None keeps everything"""
    cache = sol.TTLCache(clock, ttl_s=100, max_items=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("a", 10)
    assert cache.get("a") == 10 and cache.get("b") == 2, "updating a key doesn't grow the cache"

    big = sol.TTLCache(clock, ttl_s=100)
    for i in range(1000):
        big.set(i, i)
    assert all(big.get(i) == i for i in range(1000)), "max_items=None means no eviction"
