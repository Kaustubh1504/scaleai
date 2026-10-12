import pytest


def check(sol, method, status, expected, key=False):
    got = sol.triage(method, status, idempotency_key=key)
    assert isinstance(got, sol.Triage), f"triage({method!r}, {status}) must return a Triage, got {type(got).__name__}"
    want = sol.Triage(*expected)
    assert got == want, f"triage({method!r}, {status}, idempotency_key={key}) -> {got}, expected {want}"


def test_success_codes(sol):
    """200, 201 and 204 are Triage("none", False, "ok")"""
    for status in (200, 201, 204):
        check(sol, "GET", status, ("none", False, "ok"))
    check(sol, "POST", 201, ("none", False, "ok"))


def test_specific_client_errors(sol):
    """400/401/403/404/409/422 map to their own action and are never retryable"""
    expected = {
        400: "fix_request", 401: "reauthenticate", 403: "forbidden",
        404: "not_found", 409: "conflict", 422: "fix_payload",
    }
    for status, action in expected.items():
        check(sol, "GET", status, ("client", False, action))
        check(sol, "POST", status, ("client", False, action), key=True)


def test_rate_limited(sol):
    """429 is blamed on the client but retryable with action back_off"""
    check(sol, "GET", 429, ("client", True, "back_off"))


def test_server_errors_on_idempotent_methods(sol):
    """500/502/503/504 on GET, PUT and DELETE are server faults to retry"""
    for method in ("GET", "PUT", "DELETE", "HEAD", "OPTIONS"):
        for status in (500, 502, 503, 504):
            check(sol, method, status, ("server", True, "retry"))


def test_post_5xx_without_key_gives_up(sol):
    """A 5xx on POST/PATCH without an idempotency key is not retryable (give_up)"""
    for method in ("POST", "PATCH"):
        for status in (500, 502, 503, 504):
            check(sol, method, status, ("server", False, "give_up"))


def test_post_5xx_with_key_retries(sol):
    """With an idempotency key, a 5xx on POST/PATCH is retryable again"""
    for method in ("POST", "PATCH"):
        for status in (500, 503, 504):
            check(sol, method, status, ("server", True, "retry"), key=True)


def test_post_429_always_backs_off(sol):
    """429 on POST is retryable with or without an idempotency key"""
    check(sol, "POST", 429, ("client", True, "back_off"))
    check(sol, "POST", 429, ("client", True, "back_off"), key=True)


def test_method_is_case_insensitive(sol):
    """Methods are compared case-insensitively ("get" is idempotent, "post" is not)"""
    check(sol, "get", 503, ("server", True, "retry"))
    check(sol, "Delete", 502, ("server", True, "retry"))
    check(sol, "post", 503, ("server", False, "give_up"))


def test_unknown_codes_fall_back_by_class(sol):
    """Unlisted codes fall back on their class: 2xx ok, 4xx fix_request, 5xx retry"""
    check(sol, "GET", 202, ("none", False, "ok"))
    check(sol, "GET", 299, ("none", False, "ok"))
    check(sol, "DELETE", 418, ("client", False, "fix_request"))
    check(sol, "GET", 410, ("client", False, "fix_request"))
    check(sol, "GET", 599, ("server", True, "retry"))
    check(sol, "GET", 507, ("server", True, "retry"))
    check(sol, "POST", 507, ("server", False, "give_up"))


def test_untriageable_codes_raise(sol):
    """1xx, 3xx and out-of-range codes raise ValueError"""
    for status in (100, 101, 301, 302, 304, 99, 0, 600, 999):
        with pytest.raises(ValueError):
            sol.triage("GET", status)
            pytest.fail(f"triage('GET', {status}) should raise ValueError")


def test_actions_come_from_vocabulary(sol):
    """Every returned action is one of ACTIONS and blame is none/client/server"""
    for method in ("GET", "POST"):
        for status in (200, 204, 400, 401, 403, 404, 409, 422, 429, 450, 500, 502, 503, 504, 550):
            got = sol.triage(method, status)
            assert got.action in sol.ACTIONS, f"{got.action!r} is not in ACTIONS"
            assert got.blame in {"none", "client", "server"}, f"bad blame {got.blame!r}"
