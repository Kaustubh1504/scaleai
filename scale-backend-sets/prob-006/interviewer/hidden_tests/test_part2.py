"""Part 2: token lifecycle and customer rollup."""

import pytest

from conftest import build_api, expected_customers, expected_projects, make_client, run_report, strip_change
from shared.mock_rest import FaultConfig


def test_customer_rollup(clock):
    api = build_api(clock)
    assert run_report(api, clock)["customers"] == expected_customers(api)


def test_proactive_refresh_never_sends_an_expired_token(clock):
    api = build_api(clock, token_ttl_s=10, faults=FaultConfig(seed=61, latency_s=1.0))
    report = run_report(api, clock)
    assert strip_change(report["projects"]) == strip_change(expected_projects(api))
    assert [e for e in api.requests("/v1") if e.status == 401] == []
    assert api.tokens_issued >= 3


def test_refresh_token_grant_is_used(clock):
    api = build_api(clock, token_ttl_s=10, faults=FaultConfig(seed=61, latency_s=1.0))
    sent = []
    inner = api.handle

    def spy(request):
        if request.url.path == "/oauth/token":
            sent.append(request.content)
        return inner(request)

    api.handle = spy
    run_report(api, clock)
    assert len(sent) >= 3
    assert sum(b"refresh_token" in body for body in sent) >= len(sent) - 1


def test_falls_back_to_client_credentials_when_refresh_fails(clock):
    api = build_api(clock, token_ttl_s=10, faults=FaultConfig(seed=61, latency_s=1.0))

    def forget_refresh_tokens(api_, request):
        api_.revoke_refresh_tokens()  # every refresh token becomes invalid -> 400 invalid_grant

    api.on_request = forget_refresh_tokens
    report = run_report(api, clock)
    assert report["totals"]["tasks_total"] == 600
    token_calls = api.requests("/oauth/token")
    assert any(e.status == 400 for e in token_calls) and any(e.status == 200 for e in token_calls[1:])


def test_revoked_token_is_refreshed_once_and_request_retried(clock):
    state = {"n": 0}

    def revoke_on_fifth(api_, request):
        if request.url.path.startswith("/v1"):
            state["n"] += 1
            if state["n"] == 5:
                api_.expire_all_tokens()

    api = build_api(clock, on_request=revoke_on_fifth)
    report = run_report(api, clock)
    assert strip_change(report["projects"]) == strip_change(expected_projects(api))
    rejected = [e for e in api.requests("/v1") if e.status == 401]
    assert len(rejected) == 1
    retried = api.requests("/v1")[api.requests("/v1").index(rejected[0]) + 1]
    assert (retried.path, retried.params) == (rejected[0].path, rejected[0].params) and retried.status == 200


def test_second_401_raises_auth_error(clock):
    from report.client import AuthError
    from report.report import build_report

    def revoke_always(api_, request):
        if request.url.path.startswith("/v1"):
            api_.expire_all_tokens()

    api = build_api(clock, on_request=revoke_always)
    with pytest.raises(AuthError):
        build_report(make_client(api, clock))
    assert len([e for e in api.requests("/v1") if e.status == 401]) == 2


def test_customer_rollup_survives_short_tokens(clock):
    api = build_api(clock, token_ttl_s=8, faults=FaultConfig(seed=61, latency_s=1.0))
    assert run_report(api, clock)["customers"] == expected_customers(api)
