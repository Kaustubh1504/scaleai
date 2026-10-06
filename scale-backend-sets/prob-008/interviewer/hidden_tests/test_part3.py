"""Part 3: idempotent payout publishing, partial failure, retries, Retry-After, timeouts."""

import pytest

from conftest import (CLIENT_SECRET, PERIOD, assert_part1, build_api, default_validator, expected_report, make_client,
                      run, spy_results, uses_gold)
from shared.mock_rest import FaultConfig, RateLimitConfig


def compute_and_publish(api, clock):
    from earnings.calc import compute_earnings
    from earnings.payouts import publish_payouts

    client = make_client(api, clock)
    report = compute_earnings(client, *PERIOD)
    return report, publish_payouts(client, report)


def payable(api, report=None):
    rows = expected_report(api, gold=report is not None and uses_gold(report))["annotators"]
    return {r["annotator_id"]: r["earnings_cents"] for r in rows if not r["on_hold"] and r["earnings_cents"] > 0}


def stored(api):
    return {r["annotator_id"]: r["amount_cents"] for r in api.canonical("results")}


# ------------------------------------------------------------------ publishing


def test_publishes_one_payout_per_payable_annotator(clock):
    api = build_api(clock, messy=False, all_active=True)
    sent = spy_results(api)
    report, outcome = compute_and_publish(api, clock)
    expected = payable(api, report)
    assert stored(api) == expected and len(api.canonical("results")) == len(expected)
    assert outcome["published"] == sorted(expected) and outcome["failed"] == []
    period = "2024-04-03T00:00:00Z/2024-04-12T00:00:00Z"
    for key, body in sent:
        assert body == {"annotator_id": body["annotator_id"], "period": period, "amount_cents": expected[body["annotator_id"]]}
        assert key == f"payout:{period}:{body['annotator_id']}"


def test_on_hold_and_zero_rows_are_not_published(clock):
    api = build_api(clock, messy=False)
    report, outcome = compute_and_publish(api, clock)
    expected = payable(api, report)
    held = [r["annotator_id"] for r in expected_report(api)["annotators"] if r["on_hold"] and r["earnings_cents"]]
    assert held, "the dataset should contain an inactive annotator with earnings"
    assert stored(api) == expected
    assert not set(held) & set(outcome["published"])


def test_rerun_creates_no_new_results(clock):
    api = build_api(clock, messy=False, all_active=True)
    _, first = compute_and_publish(api, clock)
    before = api.canonical("results")
    _, second = compute_and_publish(api, clock)
    assert api.canonical("results") == before
    assert second["published"] == first["published"] and second["failed"] == []


def test_lost_response_is_retried_without_paying_twice(clock):
    # "malformed": the sink stores the payout but the 201 body is cut off; "timeout": no answer at all.
    api = build_api(clock, messy=False, all_active=True,
                    faults=FaultConfig(seed=83, scripted={"POST /v1/results": ["malformed", 503, "ok", "timeout", "malformed"]}))
    report, outcome = compute_and_publish(api, clock)
    expected = payable(api, report)
    assert stored(api) == expected and len(api.canonical("results")) == len(expected)
    assert outcome["failed"] == []
    assert any(e.status == 200 for e in api.requests("/v1/results", method="POST"))  # the replay


def test_one_failing_payout_does_not_stop_the_others(clock):
    api = build_api(clock, messy=False, all_active=True)
    victim = sorted(payable(api))[1]  # who is payable does not depend on the gold bonus
    sent = spy_results(api, fail_for={victim}, status=503)
    report, outcome = compute_and_publish(api, clock)
    expected = payable(api, report)
    assert outcome["failed"] == [victim]
    assert outcome["published"] == sorted(set(expected) - {victim})
    assert stored(api) == {k: v for k, v in expected.items() if k != victim}
    assert sum(body["annotator_id"] == victim for _, body in sent) == 4  # retried up to the attempt cap


def test_rejected_payout_is_not_retried(clock):
    victim = sorted(payable(build_api(clock, messy=False, all_active=True)))[0]
    validator = lambda body: "account frozen" if body.get("annotator_id") == victim else default_validator(body)  # noqa: E731
    api = build_api(clock, messy=False, all_active=True, validator=validator)
    sent = spy_results(api)
    _, outcome = compute_and_publish(api, clock)
    assert outcome["failed"] == [victim]
    assert sum(body["annotator_id"] == victim for _, body in sent) == 1
    assert victim not in stored(api) and len(outcome["published"]) == len(stored(api)) > 0


# ------------------------------------------------------------------ retries on reads


def test_transient_5xx_retried_with_backoff(clock):
    api = build_api(clock, messy=False, faults=FaultConfig(seed=83, scripted={"GET /v1/reviews": [503, 500]}))
    assert_part1(api, run(api, clock))
    assert len(clock.sleeps) == 2
    assert 0.25 <= clock.sleeps[0] <= 0.5 and 0.5 <= clock.sleeps[1] <= 1.0


def test_gives_up_after_four_attempts(clock):
    from earnings.client import ApiError

    api = build_api(clock, messy=False, faults=FaultConfig(seed=83, scripted={"GET /v1/tasks": [502] * 6}))
    with pytest.raises(ApiError):
        run(api, clock)
    assert len([e for e in api.requests("/v1/tasks") if e.status == 502]) == 4
    assert len(clock.sleeps) == 3


def test_retry_after_is_honoured_exactly(clock):
    api = build_api(clock, messy=False, faults=FaultConfig(seed=83, scripted={"GET /v1/submissions": ["429:4", "429:2"]}))
    assert_part1(api, run(api, clock))
    assert clock.sleeps == [4.0, 2.0]


def test_429s_do_not_use_up_attempts(clock):
    api = build_api(clock, messy=False, faults=FaultConfig(seed=83, scripted={"GET /v1/reviews": [
        "429:1", 503, "429:1", 503, "429:1", 503, "429:1"]}))
    assert_part1(api, run(api, clock))


def test_ten_consecutive_429s_give_up(clock):
    from earnings.client import ApiError

    api = build_api(clock, messy=False, faults=FaultConfig(seed=83, scripted={"GET /v1/annotators": ["429:1"] * 12}))
    with pytest.raises(ApiError):
        run(api, clock)
    assert len(api.requests("/v1/annotators")) == 10


def test_timeout_and_malformed_body_are_transient(clock):
    api = build_api(clock, messy=False, faults=FaultConfig(seed=83, slow_latency_s=30,
                                                           scripted={"GET /v1/annotators": ["timeout", "malformed"]}))
    assert_part1(api, run(api, clock))
    assert [e.outcome for e in api.requests("/v1/annotators")][:3] == ["timeout", "fault:malformed", "ok"]


def test_ten_second_timeout(clock):
    api = build_api(clock, messy=False, faults=FaultConfig(seed=83, latency_s=8.0))  # > httpx's 5 s default
    assert_part1(api, run(api, clock))
    assert all(e.outcome != "timeout" for e in api.log)


def test_token_endpoint_is_retried(clock):
    api = build_api(clock, messy=False, faults=FaultConfig(seed=83, scripted={"POST /oauth/token": [503, "malformed"]}))
    assert_part1(api, run(api, clock))


def test_real_rate_limit_end_to_end(clock):
    api = build_api(clock, messy=False, all_active=True, rate_limit=RateLimitConfig(requests=4, window_s=2))
    report, outcome = compute_and_publish(api, clock)
    assert_part1(api, report)
    assert stored(api) == payable(api, report) and outcome["failed"] == []
    log = api.requests("/v1")
    limited = [i for i, e in enumerate(log) if e.status == 429]
    assert limited
    for i in limited:
        assert log[i + 1].at >= log[i].at + 1


def test_bad_secret_still_raises_auth_error(clock):
    from earnings.calc import compute_earnings
    from earnings.client import AuthError

    api = build_api(clock, messy=False)
    with pytest.raises(AuthError):
        compute_earnings(make_client(api, clock, client_secret=CLIENT_SECRET + "x"), *PERIOD)
    assert len(api.requests("/oauth/token")) == 1  # a 401 from the token endpoint is not retried
