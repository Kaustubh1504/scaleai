import random
from email.utils import formatdate

import pytest

from problem_api import make_api

PATH = "/v1/batches/bat_001"
KEY = f"GET {PATH}"
T = 1_700_000_000.0


def http_date(t):
    return formatdate(t, usegmt=True)


def call(sol, api, clock, path=PATH, **kwargs):
    return sol.request_respecting_429(api.client(), "GET", path, clock=clock, rng=random.Random(0), **kwargs)


def test_parse_integer_seconds(sol):
    """retry_after_seconds("7", ...) is 7.0"""
    assert sol.retry_after_seconds("7", http_date(T), T) == pytest.approx(7.0)
    assert sol.retry_after_seconds("120", None, T) == pytest.approx(120.0)


def test_parse_http_date_against_date_header(sol):
    """An HTTP-date is measured from the response's Date header, not from your clock"""
    wait = sol.retry_after_seconds(http_date(T + 30), http_date(T), now=T - 3600)
    assert wait == pytest.approx(30.0), \
        f"Retry-After is 30 s after the server's Date; got {wait} (did you subtract your own clock?)"


def test_parse_http_date_without_date_header(sol):
    """With no usable Date header, an HTTP-date is measured from `now`"""
    assert sol.retry_after_seconds(http_date(T + 20), None, now=T) == pytest.approx(20.0)
    assert sol.retry_after_seconds(http_date(T + 20), "garbage", now=T) == pytest.approx(20.0)


def test_parse_missing_or_junk_defaults_to_one_second(sol):
    """Missing, empty, junk and negative Retry-After values all mean 1 second"""
    for value in (None, "", "soon", "-5", "Wed, 99 Foo 20xx"):
        got = sol.retry_after_seconds(value, http_date(T), T)
        assert got == pytest.approx(1.0), f"Retry-After {value!r} should give 1.0, got {got}"


def test_parse_date_in_the_past_defaults_to_one_second(sol):
    """An HTTP-date before the Date header means 1 second, never a negative sleep"""
    assert sol.retry_after_seconds(http_date(T - 60), http_date(T), T) == pytest.approx(1.0)


def test_waits_integer_retry_after(sol, clock):
    """A 429 with Retry-After: 3 sleeps exactly 3 s, then returns the batch"""
    api = make_api(clock)
    api.script(KEY, ["429:3"])
    resp = call(sol, api, clock)
    assert resp.json()["id"] == "bat_001"
    assert clock.sleeps == [pytest.approx(3.0)], f"expected one 3 s sleep, got {clock.sleeps}"
    assert len(api.log) == 2


def test_waits_http_date_retry_after_with_skewed_server(sol, clock):
    """An HTTP-date Retry-After 12 s after the server's Date sleeps 12 s, although the server clock is 1 h ahead"""
    api = make_api(clock, server_skew_s=3600.0)
    api.script(KEY, [api.too_many_in(12)])
    resp = call(sol, api, clock)
    assert resp.status_code == 200
    assert clock.sleeps == [pytest.approx(12.0)], \
        f"expected one 12 s sleep, got {clock.sleeps} (use the response's Date header, not clock.time())"


def test_missing_and_junk_header_waits_one_second(sol, clock):
    """429s with no Retry-After or a junk one each sleep 1 s"""
    api = make_api(clock)
    api.script(KEY, ["429", api.too_many("soon"), api.too_many("-5")])
    call(sol, api, clock)
    assert clock.sleeps == [pytest.approx(1.0)] * 3, f"expected three 1 s sleeps, got {clock.sleeps}"


def test_gives_up_after_too_many_429s(sol, clock):
    """Five 429s in a row are fine; the sixth raises RateLimitedError without sleeping"""
    api = make_api(clock)
    api.script(KEY, ["429:1"] * 5)
    assert call(sol, api, clock).status_code == 200, "5 consecutive 429s are within max_429s=5"

    clock.sleeps.clear()
    api2 = make_api(clock)
    api2.script(KEY, ["429:1"] * 6 + ["pass"])
    with pytest.raises(sol.RateLimitedError) as exc:
        call(sol, api2, clock)
    assert exc.value.path == PATH
    assert len(api2.log) == 6, f"stop at the 6th 429, made {len(api2.log)} requests"
    assert len(clock.sleeps) == 5, "sleep after each of the first five 429s, not after the sixth"


def test_429s_do_not_use_up_attempts(sol, clock):
    """With max_attempts=2, a 503 then three 429s still succeeds: 429s aren't counted attempts"""
    api = make_api(clock)
    api.script(KEY, [503, "429:2", "429:2", "429:2"])
    resp = call(sol, api, clock, max_attempts=2)
    assert resp.status_code == 200, "only the 503 counts toward max_attempts"
    assert len(api.log) == 5
    assert 0.25 <= clock.sleeps[0] <= 0.5, "the 503 gets a normal jittered backoff"
    assert clock.sleeps[1:] == [pytest.approx(2.0)] * 3, "each 429 sleeps its Retry-After, no jitter"


def test_streak_resets_after_other_outcome(sol, clock):
    """The 429 streak resets on a non-429: four 429s, a 503, four more 429s, then success"""
    api = make_api(clock)
    api.script(KEY, ["429:1"] * 4 + [503] + ["429:1"] * 4)
    resp = call(sol, api, clock)
    assert resp.status_code == 200, "the 503 breaks the streak, so neither run exceeds 5"
    assert len(api.log) == 10


def test_other_errors_raise_api_error(sol, clock):
    """A 403 raises ApiError(403) at once; four 503s raise ApiError(503, attempts=4)"""
    api = make_api(clock)
    with pytest.raises(sol.ApiError) as exc:
        call(sol, api, clock, path="/v1/batches/bat_locked")
    assert exc.value.status == 403
    assert len(api.log) == 1, "a 403 is not retryable"

    api2 = make_api(clock)
    api2.script(KEY, [503] * 4)
    with pytest.raises(sol.ApiError) as exc:
        call(sol, api2, clock)
    assert exc.value.status == 503
    assert exc.value.attempts == 4
    assert len(api2.log) == 4
