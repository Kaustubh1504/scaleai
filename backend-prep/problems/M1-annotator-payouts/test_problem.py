import random
from datetime import datetime, timezone

import pytest

from problem_api import CLIENT_ID, CLIENT_SECRET, make_api, sample_data

START = datetime(2024, 5, 1, tzinfo=timezone.utc)
END = datetime(2024, 5, 15, tzinfo=timezone.utc)
PERIOD = "2024-05-01T00:00:00Z/2024-05-15T00:00:00Z"
COUNTS = ("annotator_id", "approved", "rejected", "pending", "amount_cents")


def ann(aid, on_hold=False, **extra):
    return {"id": aid, "name": aid.upper(), "on_hold": on_hold, **extra}


def task(tid, reward=10):
    return {"id": tid, "project": "p", "reward_cents": reward}


def sub(sid, aid, tid, at, *reviews):
    return {"id": sid, "annotator_id": aid, "task_id": tid, "submitted_at": at,
            "reviews": [{"id": r, "verdict": v, "reviewed_at": t} for r, v, t in reviews]}


def ok(rid="rev_x", at="2024-05-20T00:00:00Z"):
    return (rid, "approved", at)


def client_for(sol, api, seed=0, secret=CLIENT_SECRET):
    return sol.PayoutClient(api.client(), CLIENT_ID, secret, clock=api.clock, rng=random.Random(seed))


def run(sol, data=None, **kw):
    api = make_api(data, **kw)
    client = client_for(sol, api)
    return api, client, sol.compute_payouts(client, START, END)


def pick(report, keys=COUNTS):
    return [tuple(r[k] for k in keys) for r in report["rows"]]


def by_id(report):
    return {r["annotator_id"]: r for r in report["rows"]}


def big_data(n_ann=60, n_tasks=120, n_subs=130):
    anns = [ann(f"ann_{i:03d}") for i in range(n_ann)]
    tasks = [task(f"task_{i:04d}", reward=i + 1) for i in range(n_tasks)]
    subs = [sub(f"sub_{i:05d}", f"ann_{i % n_ann:03d}", f"task_{i % n_tasks:04d}",
                f"2024-05-02T{i // 60:02d}:{i % 60:02d}:00Z", ok(f"rev_{i:05d}"))
            for i in range(n_subs)]
    expected: dict[str, int] = {}
    for i in range(n_subs):
        expected[f"ann_{i % n_ann:03d}"] = expected.get(f"ann_{i % n_ann:03d}", 0) + (i % n_tasks) + 1
    return {"annotators": anns, "tasks": tasks, "submissions": subs}, expected


# ------------------------------------------------------------------ part 1


def test_part1_sample_report(sol):
    """Sample data: the exact rows, amounts (integer cents) and total for the period"""
    _, _, report = run(sol)
    assert report["period"] == PERIOD
    assert pick(report, ("annotator_id", "name", "approved", "rejected", "pending", "amount_cents")) == [
        ("ann_001", "Ana", 2, 0, 0, 65),
        ("ann_002", "Bo", 0, 1, 1, 0),
        ("ann_003", "Chen", 1, 0, 0, 30),
        ("ann_005", "Eli", 2, 0, 0, 35),
        ("ann_006", "Fay", 0, 1, 0, 0),
    ], "rows wrong (see the worked example in the statement)"
    assert report["total_cents"] == 130
    assert all(type(r["amount_cents"]) is int for r in report["rows"]), "money must be int cents, never float"


def test_part1_follows_every_page(sol):
    """Follows page-number, offset and cursor pagination to the end of all three collections"""
    data, expected = big_data()
    api, _, report = run(sol, data)
    assert {r["annotator_id"]: r["amount_cents"] for r in report["rows"]} == expected, \
        "some annotators, tasks or submissions were missed"
    assert report["total_cents"] == sum(expected.values())
    for path in ("/v1/annotators", "/v1/tasks", "/v1/submissions"):
        assert len(api.calls("GET", path)) >= 3, f"{path} has several pages; did you follow them?"
    assert not [c for c in api.log if c.status == 400], "a request was rejected with 400 (bad page params?)"
    assert "cursor" not in api.calls("GET", "/v1/submissions")[0].params, "first page must not send a cursor"


def test_part1_period_is_half_open(sol):
    """A submission at period_start is in; one at period_end (or before start) is out"""
    data = {"annotators": [ann("a1"), ann("a2"), ann("a3"), ann("a4")], "tasks": [task("t1", 7)],
            "submissions": [sub("s1", "a1", "t1", "2024-05-01T00:00:00Z", ok()),
                            sub("s2", "a2", "t1", "2024-05-14T23:59:59Z", ok()),
                            sub("s3", "a3", "t1", "2024-05-15T00:00:00Z", ok()),
                            sub("s4", "a4", "t1", "2024-04-30T23:59:59Z", ok())]}
    _, _, report = run(sol, data)
    assert [r["annotator_id"] for r in report["rows"]] == ["a1", "a2"], "start is inclusive, end is exclusive"
    assert report["total_cents"] == 14


def test_part1_latest_review_decides(sol):
    """The latest review decides (any list order); ties go to the greatest review id; late reviews count"""
    data = {"annotators": [ann("a1")], "tasks": [task("t1", 5)],
            "submissions": [
                sub("s1", "a1", "t1", "2024-05-02T00:00:00Z",          # latest listed first
                    ("rev_09", "approved", "2024-05-06T00:00:00Z"), ("rev_10", "rejected", "2024-05-03T00:00:00Z")),
                sub("s2", "a1", "t1", "2024-05-02T00:00:00Z",          # tie: rev_20 > rev_19
                    ("rev_20", "rejected", "2024-05-06T00:00:00Z"), ("rev_19", "approved", "2024-05-06T00:00:00Z")),
                sub("s3", "a1", "t1", "2024-05-02T00:00:00Z",          # review after period_end
                    ("rev_30", "rejected", "2024-05-03T00:00:00Z"), ("rev_31", "approved", "2024-06-30T00:00:00Z")),
            ]}
    _, _, report = run(sol, data)
    assert pick(report) == [("a1", 2, 1, 0, 10)], "s1 approved, s2 rejected (tie -> rev_20), s3 approved"


def test_part1_rows_only_for_active_annotators(sol):
    """Rows exist only for annotators with a submission in the period, sorted by id; no review = pending"""
    data = {"annotators": [ann("c"), ann("b"), ann("a"), ann("idle")], "tasks": [task("t1", 3)],
            "submissions": [sub("s1", "c", "t1", "2024-05-03T00:00:00Z"),
                            sub("s2", "a", "t1", "2024-05-03T00:00:00Z", ok()),
                            sub("s3", "b", "t1", "2024-05-03T00:00:00Z", ("r", "rejected", "2024-05-04T00:00:00Z")),
                            sub("s4", "idle", "t1", "2024-06-03T00:00:00Z", ok())]}
    _, _, report = run(sol, data)
    assert pick(report) == [("a", 1, 0, 0, 3), ("b", 0, 1, 0, 0), ("c", 0, 0, 1, 0)]


def test_part1_token_fetched_once(sol):
    """Gets one token with the client credentials and sends it as a Bearer token on every /v1 request"""
    api, _, _ = run(sol)
    token_calls = api.calls("POST", "/oauth/token")
    assert len(token_calls) == 1, "reuse the token; don't fetch one per request"
    assert token_calls[0].json() == {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
    v1 = [c for c in api.log if c.path.startswith("/v1")]
    assert v1 and all(c.header("authorization") == "Bearer tok_00001" for c in v1)


def test_part1_bad_credentials_raise_auth_error(sol):
    """Wrong client credentials raise AuthError (a subclass of ApiError)"""
    api = make_api()
    client = client_for(sol, api, secret="wrong")
    with pytest.raises(sol.AuthError) as exc:
        sol.compute_payouts(client, START, END)
    assert isinstance(exc.value, sol.ApiError)
    assert exc.value.status == 401


def test_part1_api_error_carries_status_and_path(sol):
    """A 403 from /v1/tasks raises ApiError with status 403 and path /v1/tasks"""
    api = make_api()
    api.script("GET /v1/tasks", [403])
    with pytest.raises(sol.ApiError) as exc:
        sol.compute_payouts(client_for(sol, api), START, END)
    assert (exc.value.status, exc.value.path) == (403, "/v1/tasks")


# ------------------------------------------------------------------ part 2


def test_part2_mixed_timestamp_formats(sol):
    """ISO with Z/offset/no offset/space, epoch seconds/ms/digit strings are all placed correctly"""
    cases = {
        "in_offset0": "2024-05-03T10:00:00+00:00",
        "in_plus2": "2024-05-15T01:30:00+02:00",       # 2024-05-14T23:30Z
        "out_plus2": "2024-05-01T01:00:00+02:00",      # 2024-04-30T23:00Z
        "in_naive_space": "2024-05-04 12:00:00",
        "in_fraction": "2024-05-04T12:00:00.250Z",
        "in_epoch_s": 1714521600,                       # exactly period_start
        "out_epoch_ms": 1715731200000,                  # exactly period_end
        "in_epoch_str": " 1714600000 ",
        "in_epoch_float": 1714600000.5,
        "in_ms_str": "1714600000000",
    }
    data = {"annotators": [ann(a) for a in cases], "tasks": [task("t1", 1)],
            "submissions": [sub(f"s_{a}", a, "t1", at, ok()) for a, at in cases.items()]}
    _, _, report = run(sol, data)
    got = sorted(r["annotator_id"] for r in report["rows"])
    assert got == sorted(a for a in cases if a.startswith("in_")), "timestamps parsed or compared wrongly"


def test_part2_invalid_timestamps(sol):
    """Unparseable submitted_at -> invalid_submissions (sorted), not counted; a review with a bad time is ignored"""
    data = {"annotators": [ann("a1")], "tasks": [task("t1", 4)],
            "submissions": [sub("s_z", "a1", "t1", None), sub("s_y", "a1", "t1", "yesterday"),
                            sub("s_x", "a1", "t1", ""), sub("s_w", "a1", "t1", "05/03/2024", ok()),
                            sub("s_ok", "a1", "t1", "2024-05-03T00:00:00Z",
                                ("rev_2", "approved", "soon"), ("rev_1", "rejected", "2024-05-04T00:00:00Z"))]}
    _, _, report = run(sol, data)
    assert report["invalid_submissions"] == ["s_w", "s_x", "s_y", "s_z"]
    assert pick(report) == [("a1", 0, 1, 0, 0)], "rev_2 has an unparseable time, so rev_1 (rejected) decides"


def test_part2_reward_parsing_and_unknown(sol):
    """reward_cents as int / digit string count; null, missing, "N/A", 12.5, -5 or no task -> unknown_reward"""
    tasks = [task("t_int", 25), task("t_str", " 40 "), task("t_null", None), task("t_na", "N/A"),
             task("t_float", 12.5), task("t_neg", -5), {"id": "t_missing", "project": "p"}]
    subs = [sub(f"s_{t['id']}", "a1", t["id"], "2024-05-03T00:00:00Z", ok()) for t in tasks]
    subs.append(sub("s_t_ghost", "a1", "t_ghost", "2024-05-03T00:00:00Z", ok()))
    subs.append(sub("s_pending", "a1", "t_null", "2024-05-03T00:00:00Z"))
    _, _, report = run(sol, {"annotators": [ann("a1")], "tasks": tasks, "submissions": subs})
    assert pick(report) == [("a1", 8, 0, 1, 65)], "unknown rewards still count as approved but earn 0"
    assert report["unknown_reward"] == ["s_t_float", "s_t_ghost", "s_t_missing", "s_t_na", "s_t_neg", "s_t_null"], \
        "only approved submissions with an unknown reward, sorted (the pending one is not listed)"


def test_part2_verdict_normalisation(sol):
    """Verdicts are case/whitespace-insensitive; unknown verdicts are ignored, not treated as the latest"""
    data = {"annotators": [ann("a1")], "tasks": [task("t1", 1)], "submissions": [
        sub("s1", "a1", "t1", "2024-05-03T00:00:00Z", ("r1", " Approved ", "2024-05-04T00:00:00Z")),
        sub("s2", "a1", "t1", "2024-05-03T00:00:00Z", ("r2", "REJECTED", "2024-05-04T00:00:00Z")),
        sub("s3", "a1", "t1", "2024-05-03T00:00:00Z", ("r3", "approved", "2024-05-04T00:00:00Z"),
            ("r4", "needs_review", "2024-05-05T00:00:00Z")),
        sub("s4", "a1", "t1", "2024-05-03T00:00:00Z", ("r5", None, "2024-05-04T00:00:00Z"),
            ("r6", "", "2024-05-05T00:00:00Z")),
    ]}
    _, _, report = run(sol, data)
    assert pick(report) == [("a1", 2, 1, 1, 2)], "s1, s3 approved; s2 rejected; s4 has no usable review -> pending"


def test_part2_on_hold(sol):
    """on_hold strings/numbers parsed (unknown -> held); held rows keep amounts but leave total_cents"""
    holds = {"h_true": "TRUE", "h_maybe": "maybe", "h_one": 1, "h_bool": True,
             "p_no": "no", "p_zero_str": " 0 ", "p_zero": 0, "p_none": None, "p_false_str": " False ", "p_bool": False}
    anns = [ann(a, on_hold=v) for a, v in holds.items()] + [{"id": "p_missing", "name": "x"}]
    subs = [sub(f"s_{a['id']}", a["id"], "t1", "2024-05-03T00:00:00Z", ok()) for a in anns]
    _, _, report = run(sol, {"annotators": anns, "tasks": [task("t1", 10)], "submissions": subs})
    flags = {r["annotator_id"]: r["on_hold"] for r in report["rows"]}
    assert flags == {a["id"]: a["id"].startswith("h_") for a in anns}, "on_hold parsed wrongly"
    assert all(r["amount_cents"] == 10 for r in report["rows"]), "held annotators still show what they earned"
    assert (report["total_cents"], report["held_cents"]) == (70, 40)


def test_part2_duplicate_submissions_counted_once(sol):
    """A submission served twice (here on different pages) is counted once"""
    data, expected = big_data(n_ann=5, n_tasks=5, n_subs=60)
    data["submissions"].append(dict(data["submissions"][0]))
    _, _, report = run(sol, data)
    assert {r["annotator_id"]: r["amount_cents"] for r in report["rows"]} == expected


def test_part2_clean_data_has_empty_extras(sol):
    """On clean data: every row has on_hold False, held_cents 0, empty unknown_reward / invalid_submissions"""
    _, _, report = run(sol)
    assert all(r["on_hold"] is False for r in report["rows"])
    assert report["held_cents"] == 0 and report["total_cents"] == 130
    assert report["unknown_reward"] == [] and report["invalid_submissions"] == []


# ------------------------------------------------------------------ part 3


def _bounds_ok(sleeps, ds):
    return len(sleeps) == len(ds) and all(d / 2 <= s <= d for s, d in zip(sleeps, ds))


def test_part3_transient_failures_are_retried_with_backoff(sol, clock):
    """5xx, timeouts, connect errors and malformed bodies are retried with jittered exponential backoff"""
    api = make_api(clock=clock)
    api.script("POST /oauth/token", [503])
    api.script("GET /v1/tasks", [502, "timeout", "malformed"])
    api.script("GET /v1/submissions", ["connect"])
    report = sol.compute_payouts(client_for(sol, api), START, END)
    assert report["total_cents"] == 130
    # token: d=0.5; tasks: d=0.5, 1, 2; submissions: d=0.5 (fetch order is up to you, so compare sorted)
    assert _bounds_ok(sorted(clock.sleeps), [0.5, 0.5, 0.5, 1.0, 2.0]), \
        f"expected waits in [d/2, d] for d = 0.5 (token) | 0.5, 1, 2 (tasks) | 0.5 (submissions), got {clock.sleeps}"


def test_part3_gives_up_after_four_attempts(sol, clock):
    """4 transient failures raise ApiError (last status, or 0 after a transport error); a 404 is not retried"""
    api = make_api(clock=clock)
    api.script("GET /v1/annotators", [503, 503, 503, 503])
    with pytest.raises(sol.ApiError) as exc:
        sol.compute_payouts(client_for(sol, api), START, END)
    assert exc.value.status == 503
    assert len(api.calls("GET", "/v1/annotators")) == 4 and len(clock.sleeps) == 3

    api = make_api(clock=clock)
    api.script("GET /v1/annotators", [503, 503, 503, "timeout"])
    with pytest.raises(sol.ApiError) as exc:
        sol.compute_payouts(client_for(sol, api), START, END)
    assert exc.value.status == 0

    api = make_api(clock=clock)
    slept = len(clock.sleeps)
    api.script("GET /v1/submissions", [404])
    with pytest.raises(sol.ApiError) as exc:
        sol.compute_payouts(client_for(sol, api), START, END)
    assert exc.value.status == 404
    assert len(api.calls("GET", "/v1/submissions")) == 1 and len(clock.sleeps) == slept, "4xx is not retried"


def test_part3_429_waits_retry_after_without_using_attempts(sol, clock):
    """429 sleeps Retry-After and does not use attempts; the 10th 429 in a row raises ApiError(429)"""
    api = make_api(clock=clock)
    api.script("GET /v1/tasks", ["429:2"] * 5 + [503, 503, 503])
    report = sol.compute_payouts(client_for(sol, api), START, END)
    assert report["total_cents"] == 130, "5 x 429 + 3 x 503 then success must still succeed"
    assert clock.sleeps[:5] == [2.0] * 5, f"wait exactly Retry-After seconds, got {clock.sleeps[:5]}"
    assert len(clock.sleeps) == 8

    api = make_api(clock=clock)
    api.script("GET /v1/tasks", ["429:1"] * 12)
    with pytest.raises(sol.ApiError) as exc:
        sol.compute_payouts(client_for(sol, api), START, END)
    assert exc.value.status == 429 and len(api.calls("GET", "/v1/tasks")) == 10


def test_part3_token_expiry_mid_crawl(sol, clock):
    """A token that expires mid-crawl is refreshed on the 401 and the crawl completes correctly"""
    data, expected = big_data()
    api = make_api(data, clock=clock, latency_s=1.0, token_ttl_s=4.0)
    report = sol.compute_payouts(client_for(sol, api), START, END)
    assert {r["annotator_id"]: r["amount_cents"] for r in report["rows"]} == expected
    assert api.tokens.issued > 1, "the token should have expired and been refreshed"
    statuses = [c.status for c in api.log if c.path.startswith("/v1")]
    assert all(not (a == b == 401) for a, b in zip(statuses, statuses[1:])), "refresh before retrying after a 401"


def test_part3_publish_pays_payable_rows_with_idempotency_keys(sol):
    """Posts only rows not on hold with amount > 0, in row order, with the right body and Idempotency-Key"""
    data = sample_data()
    data["annotators"][4]["on_hold"] = "yes"    # ann_005
    api, client, report = run(sol, data)
    result = sol.publish_payouts(client, report)
    assert result == {"paid": ["ann_001", "ann_003"], "failed": []}
    posts = api.calls("POST", "/v1/payouts")
    assert [p.json() for p in posts] == [
        {"annotator_id": "ann_001", "period": PERIOD, "amount_cents": 65},
        {"annotator_id": "ann_003", "period": PERIOD, "amount_cents": 30}]
    assert [p.header("idempotency-key") for p in posts] == [f"{PERIOD}:ann_001", f"{PERIOD}:ann_003"]


def test_part3_rerun_never_pays_twice(sol):
    """Publishing the same report again (even from a new client) creates no new payouts and reports them paid"""
    api, client, report = run(sol)
    sol.publish_payouts(client, report)
    again = sol.publish_payouts(client_for(sol, api, seed=1), report)
    assert again == {"paid": ["ann_001", "ann_003", "ann_005"], "failed": []}
    assert len(api.payouts) == 3, "a re-run must not create new payouts"


def test_part3_malformed_post_is_stored_once(sol):
    """A malformed reply to a POST is retried with the same key: paid, and stored exactly once"""
    api, client, report = run(sol)
    api.script("POST /v1/payouts", ["malformed"])
    result = sol.publish_payouts(client, report)
    assert result["paid"] == ["ann_001", "ann_003", "ann_005"]
    keys = [c.header("idempotency-key") for c in api.calls("POST", "/v1/payouts")]
    assert keys[:2] == [f"{PERIOD}:ann_001"] * 2, "retry the same payout with the same key"
    assert len(api.payouts) == 3


def test_part3_failed_payout_does_not_stop_the_run(sol):
    """A payout that keeps failing (or gets 409) is listed in failed and the others still go out"""
    api, client, report = run(sol)
    api.payouts[f"{PERIOD}:ann_003"] = {"id": "pay_9999", "annotator_id": "ann_003", "period": PERIOD,
                                        "amount_cents": 1}   # conflicting earlier payout -> 409
    api.script("POST /v1/payouts", [503, 503, 503, 503])
    result = sol.publish_payouts(client, report)
    assert result == {"paid": ["ann_005"], "failed": ["ann_001", "ann_003"]}
