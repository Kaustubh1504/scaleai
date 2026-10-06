"""Part 1: full pagination of four differently-paginated collections, joins, verdicts, integer cents (clean data)."""

import pytest

from conftest import (EVERYTHING, PERIOD, add_scenario, assert_part1, build_api, expected_report, make_client, row_for,
                      run, uses_gold)
from shared.mock_rest import FaultConfig


def test_report_matches_oracle(clock):
    api = build_api(clock, messy=False)
    assert_part1(api, run(api, clock))


def test_whole_history_reads_every_page_of_every_collection(clock):
    api = build_api(clock, messy=False)
    report = run(api, clock, EVERYTHING)
    assert_part1(api, report, EVERYTHING)
    assert report["totals"]["approved"] + report["totals"]["rejected"] + report["totals"]["pending"] \
        == len(api.canonical("submissions"))
    ok = [e for e in api.requests("/v1") if e.status == 200]
    assert any(int(e.params.get("offset", 0)) > 0 for e in ok if e.path == "/v1/annotators")
    assert any(int(e.params.get("page", 1)) > 1 for e in ok if e.path == "/v1/reviews")
    assert any(e.params.get("cursor") for e in ok if e.path == "/v1/tasks")
    assert any(e.params.get("cursor") for e in ok if e.path == "/v1/submissions")


def test_latest_review_wins_and_period_is_half_open(clock):
    api = build_api(clock, messy=False)
    add_scenario(api)
    report = run(api, clock)
    row = row_for(report, "ann_900")
    assert row is not None
    assert (row["approved"], row["rejected"], row["pending"], row["earnings_cents"]) == (3, 1, 1, 63)
    assert row["handle"] == "handle-ann_900"
    assert row_for(report, "ann_901") is None  # its only submission is exactly at period_end


def test_rows_sorted_one_per_annotator_with_integer_cents(clock):
    api = build_api(clock, messy=False)
    report = run(api, clock)
    ids = [r["annotator_id"] for r in report["annotators"]]
    assert ids == sorted(ids) and len(ids) == len(set(ids)) and ids
    for value in [r["earnings_cents"] for r in report["annotators"]] + [report["totals"]["earnings_cents"]]:
        assert type(value) is int


def test_totals_and_period(clock):
    api = build_api(clock, messy=False)
    report = run(api, clock)
    rows = report["annotators"]
    assert report["period"] == "2024-04-03T00:00:00Z/2024-04-12T00:00:00Z"
    assert report["totals"]["annotators"] == len(rows)
    for key in ("approved", "rejected", "pending", "earnings_cents"):
        assert report["totals"][key] == sum(r[key] for r in rows)


def test_non_2xx_raises_api_error_with_status_and_path(clock):
    from earnings.client import ApiError

    api = build_api(clock, messy=False, faults=FaultConfig(seed=83, scripted={"GET /v1/reviews": [404] * 20}))
    with pytest.raises(ApiError) as exc:
        run(api, clock)
    assert exc.value.status == 404 and "/v1/reviews" in (exc.value.path or "")


def test_bad_credentials_raise_auth_error(clock):
    from earnings.calc import compute_earnings
    from earnings.client import ApiError, AuthError

    assert issubclass(AuthError, ApiError)
    api = build_api(clock, messy=False)
    with pytest.raises(AuthError):
        compute_earnings(make_client(api, clock, client_secret="wrong"), *PERIOD)


@pytest.mark.change
def test_gold_bonus_matches_oracle(clock):
    api = build_api(clock, messy=False)
    report = run(api, clock, EVERYTHING)
    assert uses_gold(report), "rows should carry gold_bonus_cents"
    assert_part1(api, report, EVERYTHING)
    assert sum(r["gold_bonus_cents"] for r in expected_report(api, EVERYTHING, gold=True)["annotators"]) > 0


@pytest.mark.change
def test_gold_bonus_rounds_down_and_ignores_case(clock):
    api = build_api(clock, messy=False)
    add_scenario(api)
    row = row_for(run(api, clock), "ann_902")
    # " CAR" on a 35-cent gold task: 35 + 17; a wrong label: 35; rejected: 0
    assert (row["approved"], row["rejected"], row["earnings_cents"], row["gold_bonus_cents"]) == (2, 1, 87, 17)
