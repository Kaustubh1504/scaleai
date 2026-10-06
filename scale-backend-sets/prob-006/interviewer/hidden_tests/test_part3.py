"""Part 3: retries, Retry-After, timeouts, malformed bodies, efficiency."""

import pytest

from conftest import build_api, expected_pages, expected_projects, run_report, strip_change
from shared.mock_rest import FaultConfig, RateLimitConfig


def assert_correct(api, report):
    assert strip_change(report["projects"]) == strip_change(expected_projects(api))


def test_transient_5xx_retried_with_backoff(clock):
    api = build_api(clock, faults=FaultConfig(seed=61, scripted={"GET /v1/projects/prj_02/tasks": [503, 500]}))
    assert_correct(api, run_report(api, clock))
    assert len(clock.sleeps) == 2
    assert 0.25 <= clock.sleeps[0] <= 0.5 and 0.5 <= clock.sleeps[1] <= 1.0


def test_jitter_is_random(clock):
    scripted = {f"GET /v1/projects/prj_{i:02d}/tasks": [502] for i in range(1, 9)}
    api = build_api(clock, faults=FaultConfig(seed=61, scripted=scripted))
    assert_correct(api, run_report(api, clock))
    assert len(clock.sleeps) == 8 and all(0.25 <= s <= 0.5 for s in clock.sleeps)
    assert len(set(clock.sleeps)) > 1


def test_gives_up_after_four_attempts(clock):
    from report.client import ApiError

    api = build_api(clock, faults=FaultConfig(seed=61, scripted={"GET /v1/projects/prj_04/tasks": [500] * 6}))
    with pytest.raises(ApiError):
        run_report(api, clock)
    assert len([e for e in api.requests("/v1/projects/prj_04/tasks") if e.status == 500]) == 4
    assert len(clock.sleeps) == 3


def test_token_endpoint_is_retried_too(clock):
    api = build_api(clock, faults=FaultConfig(seed=61, scripted={"POST /oauth/token": [503, "malformed"]}))
    assert_correct(api, run_report(api, clock))


def test_malformed_body_and_timeout_are_transient(clock):
    api = build_api(clock, faults=FaultConfig(seed=61, slow_latency_s=30,
                                              scripted={"GET /v1/projects/prj_05/tasks": ["malformed", "timeout"]}))
    assert_correct(api, run_report(api, clock))
    assert [e.outcome for e in api.requests("/v1/projects/prj_05/tasks")][:3] == ["fault:malformed", "timeout", "ok"]


def test_ten_second_timeout(clock):
    # 8 s responses succeed with timeout=10 but not with httpx's 5 s default.
    api = build_api(clock, faults=FaultConfig(seed=61, latency_s=8.0))
    assert_correct(api, run_report(api, clock))
    assert all(e.outcome != "timeout" for e in api.log)


def test_retry_after_seconds_is_honoured_exactly(clock):
    api = build_api(clock, faults=FaultConfig(seed=61, scripted={"GET /v1/projects?": ["429:7", "429:3"]}))
    assert_correct(api, run_report(api, clock))
    assert clock.sleeps[:2] == [7.0, 3.0]


def test_retry_after_http_date_under_a_real_limit(clock):
    api = build_api(clock, rate_limit=RateLimitConfig(requests=5, window_s=10, retry_after_format="http-date"))
    assert_correct(api, run_report(api, clock))
    log = api.requests("/v1")
    limited = [i for i, e in enumerate(log) if e.status == 429]
    assert limited, "the limit should have been hit"
    for i in limited:
        nxt = log[i + 1]
        assert nxt.at >= log[i].at + 1  # waited for the window instead of hammering
    assert len(limited) < 3 * len([e for e in log if e.status == 200])


def test_429s_do_not_use_up_attempts(clock):
    api = build_api(clock, faults=FaultConfig(seed=61, scripted={"GET /v1/projects/prj_06/tasks": [
        "429:1", 503, "429:1", 503, "429:1", 503, "429:1"]}))
    assert_correct(api, run_report(api, clock))


def test_ten_consecutive_429s_give_up(clock):
    from report.client import ApiError

    api = build_api(clock, faults=FaultConfig(seed=61, scripted={"GET /v1/projects/prj_07/tasks": ["429:1"] * 12}))
    with pytest.raises(ApiError):
        run_report(api, clock)
    assert len(api.requests("/v1/projects/prj_07/tasks")) == 10


def test_each_page_fetched_once_with_max_page_sizes(clock):
    api = build_api(clock, projects=23, tasks=900)
    run_report(api, clock)
    gets = [e for e in api.requests("/v1") if e.method == "GET"]
    assert len(gets) == expected_pages(api)
    keys = [(e.path, tuple(sorted(e.params.items()))) for e in gets]
    assert len(keys) == len(set(keys))
    assert all(e.params.get("per_page") == "10" for e in gets if e.path == "/v1/projects")
    assert all(e.params.get("limit") == "25" for e in gets if e.path.endswith("/tasks"))
