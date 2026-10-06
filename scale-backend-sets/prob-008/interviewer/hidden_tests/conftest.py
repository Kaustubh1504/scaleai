"""Acceptance tests for prob-008.

    SOLUTION_DIR=/path/to/candidate python -m pytest interviewer/hidden_tests [-m "not change"]

The API is built here from shared/ (not from the candidate's mock_services) with
a different seed, sizes and credentials than the candidate's defaults, and
expected values come from an independent oracle over the canonical data.
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

HERE = Path(__file__).resolve().parent
SOLUTION_DIR = Path(os.environ.get("SOLUTION_DIR", HERE.parent / "reference")).resolve()
sys.path.insert(0, str(SOLUTION_DIR))

import mock_services  # noqa: E402,F401  (puts shared/ on sys.path)
from shared.fake_clock import FakeClock  # noqa: E402
from shared.mock_rest import AuthConfig, FaultConfig, FieldMess, MockRestAPI, ResourceConfig, scale_records  # noqa: E402

SEED = 83
CLIENT_ID, CLIENT_SECRET = "hidden-finance", "hidden-secret"
UTC = timezone.utc
PERIOD = (datetime(2024, 4, 3, tzinfo=UTC), datetime(2024, 4, 12, tzinfo=UTC))
EVERYTHING = (datetime(2024, 3, 1, tzinfo=UTC), datetime(2024, 6, 1, tzinfo=UTC))
TS_MESS = ["epoch", "epoch_ms", "iso_naive", "iso_offset"]
PART1_ROW_KEYS = ("annotator_id", "handle", "approved", "rejected", "pending", "earnings_cents")
PART1_TOTAL_KEYS = ("annotators", "approved", "rejected", "pending", "earnings_cents")


def pytest_report_header(config):
    return f"solution under test: {SOLUTION_DIR}"


def pytest_configure(config):
    config.addinivalue_line("markers", "change: the mid-part requirement change (deselect with -m 'not change')")


@pytest.fixture
def clock():
    return FakeClock(start=1_714_550_400)  # 2024-05-01T08:00:00Z


# ------------------------------------------------------------------ the API


def _iso(moment):
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_records(seed, messy, annotators, tasks):
    data = scale_records(seed, annotators=annotators, tasks=tasks)
    rng = random.Random(f"earnings-reviews|{seed}")
    submitter = {s["id"]: s["annotator_id"] for s in data["submissions"]}
    extra = []
    for review in data["reviews"]:
        if rng.random() >= 0.3:
            continue
        first = _ts(review["created_at"])
        kind = rng.choice(["later", "earlier", "same"])
        moment = {"later": first + timedelta(minutes=rng.randint(30, 3000)),
                  "earlier": first - timedelta(minutes=rng.randint(1, 9)), "same": first}[kind]
        reviewer = rng.choice([a["id"] for a in data["annotators"] if a["id"] != submitter[review["submission_id"]]])
        extra.append({"id": f"rev_{len(data['reviews']) + len(extra) + 1:05d}", "submission_id": review["submission_id"],
                      "reviewer_id": reviewer, "verdict": rng.choice(["approved", "rejected"]),
                      "score": rng.randint(1, 5), "comment": "Re-review.", "created_at": _iso(moment),
                      "updated_at": _iso(moment)})
    data["reviews"].extend(extra)
    if messy:
        rewards = random.Random(f"earnings-rewards|{seed}")
        for task in data["tasks"]:
            roll = rewards.random()
            if roll < 0.06:
                task["reward_cents"] = None
            elif roll < 0.10:
                del task["reward_cents"]
    return data


def default_validator(body):
    amount = body.get("amount_cents")
    if not isinstance(body.get("annotator_id"), str) or not isinstance(body.get("period"), str):
        return "annotator_id and period must be strings"
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        return "amount_cents must be a positive integer"
    return None


def build_api(clock, *, messy, seed=SEED, annotators=45, tasks=420, faults=None, rate_limit=None,
              validator=default_validator, all_active=False, mess_rate=0.4):
    data = build_records(seed, messy, annotators, tasks)
    if all_active:
        for annotator in data["annotators"]:
            annotator["is_active"] = True
    m = (lambda rules: rules) if messy else (lambda rules: [])
    resources = [
        ResourceConfig("annotators", data["annotators"], pagination="offset", default_page_size=10, max_page_size=20,
                       mess=m([FieldMess("is_active", ["bool_str", "bool_int"], mess_rate),
                               FieldMess("hourly_rate_cents", ["str", "float"], 0.2),
                               FieldMess("skills", ["csv"], 0.25), FieldMess("country", ["lower", "null"], 0.1)])),
        ResourceConfig("tasks", data["tasks"], pagination="cursor", default_page_size=25, max_page_size=100,
                       mess=m([FieldMess("reward_cents", ["str"], mess_rate), FieldMess("priority", ["str"], 0.15),
                               FieldMess("tags", ["csv", "missing"], 0.2), FieldMess("created_at", TS_MESS, 0.2),
                               FieldMess("status", ["upper", "padded"], 0.1)])),
        ResourceConfig("submissions", data["submissions"], pagination="cursor", default_page_size=50,
                       max_page_size=100, parent=("tasks", "task_id"),
                       mess=m([FieldMess("submitted_at", TS_MESS, mess_rate),
                               FieldMess("answer.label", ["upper", "padded"], mess_rate),
                               FieldMess("answer.confidence", ["str", "null"], 0.15),
                               FieldMess("answer.boxes", ["missing", "null"], 0.1),
                               FieldMess("duration_s", ["str"], 0.15)])),
        ResourceConfig("reviews", data["reviews"], pagination="page", default_page_size=20, max_page_size=50,
                       parent=("submissions", "submission_id"),
                       mess=m([FieldMess("verdict", ["upper", "padded"], mess_rate),
                               FieldMess("created_at", TS_MESS, mess_rate), FieldMess("score", ["str"], 0.15),
                               FieldMess("comment", ["missing", "empty_str"], 0.3)])),
        ResourceConfig("results", [], pagination="page", default_page_size=20, max_page_size=50, writable=True,
                       updated_field=None, validator=validator),
    ]
    return MockRestAPI(resources, clock=clock, faults=faults or FaultConfig(seed=seed), rate_limit=rate_limit,
                       auth=AuthConfig(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))


def make_client(api, clock, *, client_secret=CLIENT_SECRET):
    from earnings.client import EarningsClient

    return EarningsClient(api.client(), CLIENT_ID, client_secret, clock)


def run(api, clock, period=PERIOD):
    from earnings.calc import compute_earnings

    return compute_earnings(make_client(api, clock), *period)


def spy_results(api, fail_for=(), status=503):
    """Record every POST /v1/results (Idempotency-Key, body); answer `status` for annotators in fail_for.
    Install before creating the client."""
    sent = []
    inner = api.handle

    def handle(request):
        if request.method == "POST" and request.url.path == "/v1/results":
            body = json.loads(request.content)
            sent.append((request.headers.get("idempotency-key"), body))
            if body.get("annotator_id") in fail_for:
                return httpx.Response(status, json={"error": "upstream_error"})
        return inner(request)

    api.handle = handle
    return sent


# ------------------------------------------------------------------ scenarios (canonical records)


def _sub(sid, task, annotator, at, label="car"):
    return {"id": sid, "task_id": task, "annotator_id": annotator, "submitted_at": at, "duration_s": 60.0,
            "answer": {"label": label, "confidence": 0.9, "boxes": []}, "updated_at": at}


def _rev(rid, sid, verdict, at):
    return {"id": rid, "submission_id": sid, "reviewer_id": "ann_001", "verdict": verdict, "score": 4,
            "comment": None, "created_at": at, "updated_at": at}


def _task(tid, reward, *, gold_label=None, drop_reward=False):
    task = {"id": tid, "project_id": "prj_01", "status": "completed", "priority": 3, "is_gold": gold_label is not None,
            "gold_label": gold_label, "payload": {"text": "x"}, "tags": [], "reward_cents": reward,
            "created_at": "2024-04-01T00:00:00Z", "completed_at": "2024-04-01T01:00:00Z",
            "updated_at": "2024-04-01T01:00:00Z"}
    if drop_reward:
        del task["reward_cents"]
    return task


def _annotator(aid, active=True):
    return {"id": aid, "handle": f"handle-{aid}", "country": "US", "level": 2, "hourly_rate_cents": 600,
            "skills": ["image_bbox"], "is_active": active, "joined_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z"}


def add_scenario(api):
    """ann_900: latest-review rule, ties, period boundaries. Expect 3 approved / 1 rejected / 1 pending, 63 cents.
    ann_901: only a submission exactly at period_end -> no row. ann_902: gold (mid-part change)."""
    for a in ("ann_900", "ann_901", "ann_902"):
        api.insert("annotators", _annotator(a))
    for t in (_task("tsk_9001", 20), _task("tsk_9002", 35), _task("tsk_9003", 8), _task("tsk_9004", 35, gold_label="car")):
        api.insert("tasks", t)
    subs = [
        _sub("sub_90001", "tsk_9001", "ann_900", "2024-04-03T00:00:00Z"),  # exactly period_start: included
        _sub("sub_90002", "tsk_9002", "ann_900", "2024-04-04T00:00:00Z"),
        _sub("sub_90003", "tsk_9003", "ann_900", "2024-04-05T00:00:00Z"),  # never reviewed: pending
        _sub("sub_90004", "tsk_9001", "ann_900", "2024-04-06T00:00:00Z"),
        _sub("sub_90005", "tsk_9002", "ann_900", "2024-04-12T00:00:00Z"),  # exactly period_end: excluded
        _sub("sub_90006", "tsk_9003", "ann_900", "2024-04-02T23:59:59Z"),  # just before: excluded
        _sub("sub_90007", "tsk_9003", "ann_900", "2024-04-11T23:00:00Z"),  # reviewed after the period
        _sub("sub_90008", "tsk_9001", "ann_901", "2024-04-12T00:00:00Z"),
        _sub("sub_90009", "tsk_9004", "ann_902", "2024-04-05T00:00:00Z", label=" CAR"),
        _sub("sub_90010", "tsk_9004", "ann_902", "2024-04-05T01:00:00Z", label="pedestrian"),
        _sub("sub_90011", "tsk_9004", "ann_902", "2024-04-05T02:00:00Z", label="car"),
    ]
    revs = [
        _rev("rev_90001", "sub_90001", "approved", "2024-04-05T10:00:00Z"),
        _rev("rev_90002", "sub_90001", "rejected", "2024-04-05T09:00:00Z"),  # higher id but older: ignored
        _rev("rev_90003", "sub_90002", "rejected", "2024-04-06T12:00:00Z"),
        _rev("rev_90004", "sub_90002", "approved", "2024-04-06T12:00:00Z"),  # same time, higher id: wins
        _rev("rev_90005", "sub_90004", "approved", "2024-04-07T00:00:00Z"),
        _rev("rev_90006", "sub_90004", "rejected", "2024-04-08T00:00:00Z"),  # newest: rejected
        _rev("rev_90007", "sub_90005", "approved", "2024-04-13T00:00:00Z"),
        _rev("rev_90008", "sub_90006", "approved", "2024-04-03T00:00:00Z"),
        _rev("rev_90009", "sub_90007", "approved", "2024-04-20T00:00:00Z"),
        _rev("rev_90010", "sub_90008", "approved", "2024-04-13T00:00:00Z"),
        _rev("rev_90011", "sub_90009", "approved", "2024-04-06T00:00:00Z"),
        _rev("rev_90012", "sub_90010", "approved", "2024-04-06T00:00:00Z"),
        _rev("rev_90013", "sub_90011", "rejected", "2024-04-06T00:00:00Z"),
    ]
    for s in subs:
        api.insert("submissions", s)
    for r in revs:
        api.insert("reviews", r)


def add_unknown_reward_scenario(api):
    """ann_903 (inactive): approved on null-reward tsk_9005 and missing-reward tsk_9006, approved on tsk_9008 (20),
    pending on tsk_9006, pending on null-reward tsk_9007 (not listed: no approved submission)."""
    api.insert("annotators", _annotator("ann_903", active=False))
    for t in (_task("tsk_9008", 20), _task("tsk_9005", None), _task("tsk_9006", None, drop_reward=True),
              _task("tsk_9007", None)):
        api.insert("tasks", t)
    for s in (_sub("sub_90012", "tsk_9005", "ann_903", "2024-04-04T00:00:00Z"),
              _sub("sub_90013", "tsk_9006", "ann_903", "2024-04-04T01:00:00Z"),
              _sub("sub_90014", "tsk_9006", "ann_903", "2024-04-04T02:00:00Z"),
              _sub("sub_90015", "tsk_9008", "ann_903", "2024-04-04T03:00:00Z"),
              _sub("sub_90016", "tsk_9007", "ann_903", "2024-04-04T04:00:00Z")):
        api.insert("submissions", s)
    for r in (_rev("rev_90014", "sub_90012", "approved", "2024-04-05T00:00:00Z"),
              _rev("rev_90015", "sub_90013", "approved", "2024-04-05T00:00:00Z"),
              _rev("rev_90016", "sub_90015", "approved", "2024-04-05T00:00:00Z")):
        api.insert("reviews", r)


# ------------------------------------------------------------------ oracle (over canonical records)


def _norm(value):
    return value.strip().lower() if isinstance(value, str) else value


def expected_report(api, period=PERIOD, *, gold=False):
    start, end = period
    tasks = {t["id"]: t for t in api.canonical("tasks")}
    annotators = {a["id"]: a for a in api.canonical("annotators")}
    latest = {}
    for r in api.canonical("reviews"):
        key = (_ts(r["created_at"]), r["id"])
        if r["submission_id"] not in latest or key > latest[r["submission_id"]][0]:
            latest[r["submission_id"]] = (key, _norm(r["verdict"]))
    rows, unknown = {}, set()
    for s in api.canonical("submissions"):
        if not start <= _ts(s["submitted_at"]) < end:
            continue
        a = s["annotator_id"]
        row = rows.setdefault(a, {"annotator_id": a, "handle": annotators[a]["handle"], "approved": 0, "rejected": 0,
                                  "pending": 0, "earnings_cents": 0, "on_hold": not annotators[a]["is_active"],
                                  "gold_bonus_cents": 0})
        verdict = latest.get(s["id"], (None, "pending"))[1]
        row[verdict] += 1
        if verdict != "approved":
            continue
        task = tasks[s["task_id"]]
        reward = task.get("reward_cents")
        if reward is None:
            unknown.add(task["id"])
            continue
        bonus = 0
        if gold and task["is_gold"] and task["gold_label"] is not None \
                and _norm(s["answer"]["label"]) == _norm(task["gold_label"]):
            bonus = reward // 2
        row["earnings_cents"] += reward + bonus
        row["gold_bonus_cents"] += bonus
    ordered = [rows[k] for k in sorted(rows)]
    if not gold:
        for row in ordered:
            del row["gold_bonus_cents"]
    totals = {"annotators": len(ordered), **{k: sum(r[k] for r in ordered) for k in ("approved", "rejected", "pending")},
              "earnings_cents": sum(r["earnings_cents"] for r in ordered),
              "payable_cents": sum(r["earnings_cents"] for r in ordered if not r["on_hold"])}
    return {"period": f"{_iso(start)}/{_iso(end)}", "annotators": ordered, "unknown_reward_task_ids": sorted(unknown),
            "totals": totals}


def uses_gold(report):
    return any("gold_bonus_cents" in row for row in report.get("annotators", []))


def part1_view(report, gold):
    keys = PART1_ROW_KEYS + (("gold_bonus_cents",) if gold else ())
    return {"period": report["period"],
            "annotators": [{k: row.get(k) for k in keys} for row in report["annotators"]],
            "totals": {k: report["totals"].get(k) for k in PART1_TOTAL_KEYS}}


def part2_view(report, gold):
    view = part1_view(report, gold)
    for out, row in zip(view["annotators"], report["annotators"]):
        out["on_hold"] = row.get("on_hold")
    view["totals"]["payable_cents"] = report["totals"].get("payable_cents")
    view["unknown_reward_task_ids"] = report.get("unknown_reward_task_ids")
    return view


def assert_part1(api, report, period=PERIOD):
    gold = uses_gold(report)
    assert part1_view(report, gold) == part1_view(expected_report(api, period, gold=gold), gold)


def assert_part2(api, report, period=PERIOD):
    gold = uses_gold(report)
    assert part2_view(report, gold) == part2_view(expected_report(api, period, gold=gold), gold)


def row_for(report, annotator_id):
    return next((r for r in report["annotators"] if r["annotator_id"] == annotator_id), None)
