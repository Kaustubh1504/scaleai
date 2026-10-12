"""42. Write the tests: catch the buggy clients: reference solution (a test suite)."""

from __future__ import annotations

import pytest

from kit import FakeClock
from problem_api import make_api


def test_fetches_every_page_in_order(impl):
    api = make_api(n_labels=25, per_page=10)
    assert impl.fetch_all(api.client(), FakeClock()) == api.labels


def test_honours_retry_after_on_429(impl):
    api = make_api(n_labels=5)
    api.script("GET /v1/labels", ["429:7"])
    clock = FakeClock()
    assert impl.fetch_all(api.client(), clock) == api.labels
    assert clock.sleeps == [7.0]


def test_does_not_retry_client_errors(impl):
    api = make_api(n_labels=5)
    api.script("GET /v1/labels", [404])
    with pytest.raises(impl.ApiError) as exc:
        impl.fetch_all(api.client(), FakeClock())
    assert exc.value.status == 404 and len(api.log) == 1


def test_gives_up_after_max_attempts_without_final_sleep(impl):
    api = make_api(n_labels=5)
    api.script("GET /v1/labels", [503] * 4)
    clock = FakeClock()
    with pytest.raises(impl.ApiError) as exc:
        impl.fetch_all(api.client(), clock, max_attempts=4, base_delay_s=1.0)
    assert exc.value.status == 503 and len(api.log) == 4
    assert clock.sleeps == [1.0, 2.0, 4.0]


def test_succeeds_on_the_last_attempt(impl):
    api = make_api(n_labels=5)
    api.script("GET /v1/labels", [503, 503, 503])
    assert impl.fetch_all(api.client(), FakeClock(), max_attempts=4) == api.labels


def test_error_on_a_later_page_raises(impl):
    api = make_api(n_labels=25, per_page=10)
    api.script("GET /v1/labels", ["pass", 500])
    with pytest.raises(impl.ApiError):
        impl.fetch_all(api.client(), FakeClock())


if __name__ == "__main__":
    import client_impl

    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test(client_impl)
    print(f"{len(tests)} tests pass against the correct client")
