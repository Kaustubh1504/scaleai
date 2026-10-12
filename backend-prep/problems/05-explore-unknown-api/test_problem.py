from collections import Counter

import httpx
import pytest

from problem_api import API_KEY, AUTH_HEADER, make_api


def expected(api):
    counts = Counter(t["customer_id"] for t in api.tickets if t["status"] == "open")
    if not counts:
        return None
    best = max(counts.values())
    cid = min(c for c, n in counts.items() if n == best)
    name = next(c["name"] for c in api.customers if c["id"] == cid)
    return {"customer_id": cid, "name": name, "open_tickets": best}


def run(sol, **kwargs):
    api = make_api(**kwargs)
    got = sol.customer_with_most_open_tickets(api.client(), API_KEY)
    return api, got


def test_default_dataset(sol):
    """Finds the right customer, name and count on the default dataset (ties -> smallest id)"""
    api, got = run(sol)
    assert got == expected(api), f"got {got}, expected {expected(api)}"


def test_several_datasets(sol):
    """Is correct across several seeds and sizes (results span many pages)"""
    for seed, n in [(1, 40), (2, 7), (3, 60), (4, 1), (5, 31)]:
        api, got = run(sol, seed=seed, n_customers=n)
        assert got == expected(api), f"seed={seed}, n_customers={n}: got {got}, expected {expected(api)}"


def test_explicit_tie_smallest_id_wins(sol):
    """Customers 4 and 9 tie with 6 open tickets: customer 4 (Globex) wins"""
    api, got = run(sol, top_ids=(9, 4))
    assert got == {"customer_id": 4, "name": "Globex", "open_tickets": 6}, got


def test_winner_on_last_customer_page(sol):
    """A clear winner that is the very last customer (id 57) is found"""
    api, got = run(sol, seed=7, n_customers=57, top_ids=(57,))
    assert got == expected(api) and got["customer_id"] == 57, f"got {got}"


def test_counts_only_open_status(sol):
    """Only status "open" counts, not pending/solved/closed"""
    api, got = run(sol, seed=11, n_customers=25)
    all_counts = Counter(t["customer_id"] for t in api.tickets)
    assert got == expected(api), \
        f"got {got}; if open_tickets looks too big you may be counting every status (busiest overall: {all_counts.most_common(1)})"


def test_no_open_tickets_returns_none(sol):
    """Returns None when no ticket is open"""
    api, got = run(sol, no_open=True)
    assert got is None, f"no open tickets anywhere, expected None, got {got}"


def test_customers_without_tickets_dont_crash(sol):
    """Customers with zero tickets are handled (only one customer has any open ticket)"""
    api = make_api(seed=3, n_customers=12, no_open=True)
    # Give exactly one customer (the highest id that has tickets) a single open ticket.
    target = max(t["customer_id"] for t in api.tickets)
    for t in api.tickets:
        if t["customer_id"] == target:
            t["status"] = "open"
            break
    got = sol.customer_with_most_open_tickets(api.client(), API_KEY)
    zero = [c["id"] for c in api.customers if not any(t["customer_id"] == c["id"] for t in api.tickets)]
    assert zero, "dataset should contain customers without tickets"
    assert got == expected(api), f"got {got}, expected {expected(api)}"


def test_sends_api_key_header(sol):
    """Every /v1 request sends the API key in the header named by the spec"""
    api, got = run(sol)
    v1 = [c for c in api.log if c.path.startswith("/v1/")]
    assert v1, "no /v1 requests were made"
    missing = [c.key for c in v1 if c.header(AUTH_HEADER) != API_KEY]
    assert not missing, f"these requests lacked {AUTH_HEADER}: {missing} (see components.securitySchemes)"


def test_reasonable_request_count(sol):
    """Makes fewer requests than there are open tickets (no request per ticket)"""
    api, got = run(sol, seed=3, n_customers=60)
    n_open = sum(t["status"] == "open" for t in api.tickets)
    assert len(api.log) < n_open, f"{len(api.log)} requests for {n_open} open tickets is too many"
    assert not api.calls("GET", "/v1/legacy/tickets"), "the legacy endpoint is deprecated (410)"


def test_http_errors_raise(sol):
    """A wrong API key surfaces as httpx.HTTPStatusError (401)"""
    api = make_api()
    with pytest.raises(httpx.HTTPStatusError) as exc:
        sol.customer_with_most_open_tickets(api.client(), "sk_wrong")
    assert exc.value.response.status_code == 401
