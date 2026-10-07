import random
from datetime import datetime, timezone

import pytest

from earnings import normalize
from earnings.calc import compute_earnings, latest_verdicts, summarize
from earnings.cli import main
from earnings.client import ApiError, AuthError, EarningsClient
from earnings.payouts import publish_payouts
from mock_services.api import CLIENT_ID, CLIENT_SECRET, make_api
from mock_services.clock import FakeClock
from shared.mock_rest import FaultConfig

UTC = timezone.utc
START, END = datetime(2024, 4, 1, tzinfo=UTC), datetime(2024, 4, 15, tzinfo=UTC)
ALL = (datetime(2024, 3, 1, tzinfo=UTC), datetime(2024, 6, 1, tzinfo=UTC))


@pytest.fixture
def clock():
    return FakeClock(start=1_714_550_400)


def client_for(api, clock, secret=CLIENT_SECRET):
    return EarningsClient(api.client(), CLIENT_ID, secret, clock, rng=random.Random(0))


# ------------------------------------------------------------------ normalize


@pytest.mark.parametrize("value", ["2024-04-02T10:00:00Z", "2024-04-02T10:00:00+00:00", "2024-04-02T10:00:00",
                                   1712052000, 1712052000000, "2024-04-02T12:00:00+02:00"])
def test_timestamps(value):
    assert normalize.parse_ts(value) == datetime(2024, 4, 2, 10, tzinfo=UTC)


@pytest.mark.parametrize("value", ["yesterday", None, True, [1]])
def test_bad_timestamps(value):
    with pytest.raises(normalize.DataError):
        normalize.parse_ts(value)


def test_rewards_flags_labels():
    assert normalize.reward_cents({"reward_cents": "12"}) == 12
    assert normalize.reward_cents({"reward_cents": None}) is None and normalize.reward_cents({}) is None
    with pytest.raises(normalize.DataError):
        normalize.reward_cents({"id": "t", "reward_cents": "12.5"})
    assert [normalize.flag(v) for v in (True, "TRUE", 1, "false", 0)] == [True, True, True, False, False]
    with pytest.raises(normalize.DataError):
        normalize.flag("yes")
    assert normalize.verdict("  APPROVED ") == "approved"
    with pytest.raises(normalize.DataError):
        normalize.verdict("maybe")


# ------------------------------------------------------------------ rules


def test_latest_review_wins_ties_by_id():
    reviews = [{"id": "rev_00001", "submission_id": "s", "verdict": "approved", "created_at": "2024-04-02T00:00:00Z"},
               {"id": "rev_00003", "submission_id": "s", "verdict": "rejected", "created_at": 1712016000},
               {"id": "rev_00002", "submission_id": "s", "verdict": "approved", "created_at": "2024-04-02T00:00:00"}]
    assert latest_verdicts(reviews) == {"s": "rejected"}


def test_summarize_unknown_rewards_hold_and_half_open_period():
    annotators = {"a": {"handle": "A", "is_active": True}, "b": {"handle": "B", "is_active": "false"}}
    tasks = {"t1": {"id": "t1", "reward_cents": "20"}, "t2": {"id": "t2"}}
    subs = [{"id": "s1", "task_id": "t1", "annotator_id": "a", "submitted_at": "2024-04-01T00:00:00Z"},
            {"id": "s2", "task_id": "t2", "annotator_id": "a", "submitted_at": "2024-04-02T00:00:00Z"},
            {"id": "s3", "task_id": "t1", "annotator_id": "b", "submitted_at": "2024-04-03T00:00:00Z"},
            {"id": "s4", "task_id": "t1", "annotator_id": "b", "submitted_at": "2024-04-15T00:00:00Z"}]
    report = summarize(annotators, tasks, subs, {"s1": "approved", "s2": "approved", "s3": "approved"}, START, END)
    rows = {r["annotator_id"]: r for r in report["annotators"]}
    assert (rows["a"]["approved"], rows["a"]["earnings_cents"], rows["a"]["on_hold"]) == (2, 20, False)
    assert (rows["b"]["approved"], rows["b"]["pending"], rows["b"]["on_hold"]) == (1, 0, True)
    assert report["unknown_reward_task_ids"] == ["t2"]
    assert report["totals"]["earnings_cents"] == 40 and report["totals"]["payable_cents"] == 20


def test_whole_dataset_matches_clean_and_messy(clock):
    clean = compute_earnings(client_for(make_api(messy=False, clock=clock), clock), *ALL)
    assert clean["totals"]["approved"] > 0 and all(isinstance(r["earnings_cents"], int) for r in clean["annotators"])
    messy = compute_earnings(client_for(make_api(clock=clock), clock), *ALL)
    assert messy["totals"]["approved"] == clean["totals"]["approved"]  # mess never changes verdicts
    assert messy["unknown_reward_task_ids"]


def test_auth_and_api_errors(clock):
    with pytest.raises(AuthError):
        compute_earnings(client_for(make_api(clock=clock), clock, secret="nope"), START, END)
    api = make_api(clock=clock, faults=FaultConfig(scripted={"GET /v1/reviews": [404]}))
    with pytest.raises(ApiError) as exc:
        compute_earnings(client_for(api, clock), START, END)
    assert exc.value.status == 404 and exc.value.path == "/v1/reviews"


# ------------------------------------------------------------------ payouts


def test_publish_is_idempotent_and_isolates_failures(clock):
    api = make_api(clock=clock)
    client = client_for(api, clock)
    report = compute_earnings(client, START, END)
    payable = [r["annotator_id"] for r in report["annotators"] if not r["on_hold"] and r["earnings_cents"] > 0]
    first = publish_payouts(client, report)
    assert first == {"published": payable, "failed": []}
    assert publish_payouts(client, report) == first
    assert len(api.canonical("results")) == len(payable)

    api = make_api(clock=clock, faults=FaultConfig(scripted={"POST /v1/results": ["malformed", 503, "ok"] + [500] * 4}))
    client = client_for(api, clock)
    outcome = publish_payouts(client, compute_earnings(client, START, END))
    assert outcome["failed"] == [payable[1]] and len(outcome["published"]) == len(payable) - 1
    # payable[0]: stored on the "malformed" attempt, then replayed -> paid exactly once
    assert len(api.canonical("results")) == len(payable) - 1
    assert sum(r["annotator_id"] == payable[0] for r in api.canonical("results")) == 1


def test_cli(tmp_path, capsys):
    api = make_api(clock=FakeClock())
    out = tmp_path / "e.csv"
    assert main(["--start", "2024-04-01", "--end", "2024-04-15", "--out", str(out), "--publish"],
                http=api.client()) == 0
    assert out.read_text().splitlines()[0].startswith("annotator_id,handle,approved")
    assert "published" in capsys.readouterr().out
