"""Tests for the existing earnings code. Add your own next to them."""

from datetime import datetime, timezone

from earnings.calc import compute_earnings, period_label, summarize
from earnings.client import EarningsClient
from mock_services.api import CLIENT_ID, CLIENT_SECRET, make_api
from mock_services.clock import FakeClock

APRIL_1 = datetime(2024, 4, 1, tzinfo=timezone.utc)
APRIL_15 = datetime(2024, 4, 15, tzinfo=timezone.utc)


def make_client(api, clock):
    return EarningsClient(api.client(), CLIENT_ID, CLIENT_SECRET, clock)


def test_mock_api_answers():
    api = make_api(clock=FakeClock())
    http = api.client()
    token = http.post("/oauth/token", json={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}).json()
    page = http.get("/v1/tasks", headers={"Authorization": f"Bearer {token['access_token']}"}).json()
    assert page["data"] and "next_cursor" in page


def test_summarize_adds_rewards():
    tasks = {"t1": {"id": "t1", "reward_cents": 20}, "t2": {"id": "t2", "reward_cents": 35}}
    subs = [{"task_id": "t1", "annotator_id": "a"}, {"task_id": "t2", "annotator_id": "a"},
            {"task_id": "t1", "annotator_id": "b"}]
    out = summarize(subs, tasks)
    assert out["a"] == {"submissions": 2, "earnings_usd": 0.55}
    assert out["b"]["submissions"] == 1


def test_period_label():
    assert period_label(APRIL_1, APRIL_15) == "2024-04-01T00:00:00Z/2024-04-15T00:00:00Z"


def test_compute_earnings_on_clean_data():
    clock = FakeClock()
    report = compute_earnings(make_client(make_api(messy=False, clock=clock), clock), APRIL_1, APRIL_15)
    assert report["annotators"]
    assert report["annotators"] == sorted(report["annotators"], key=lambda r: r["annotator_id"])
    assert report["totals"]["earnings_cents"] > 0
