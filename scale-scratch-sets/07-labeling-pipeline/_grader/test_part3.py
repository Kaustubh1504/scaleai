"""Part 3: signed customer callbacks with retries, idempotency keys, bounded concurrency."""

import csv
import hashlib
import hmac
import json
import logging
import time
from pathlib import Path

import pytest
from conftest import CALLBACK_SECRET, HERE, keyed, run

EXPECTED = json.loads((HERE / "expected_sample.json").read_text())


def by_id(name="labels.json"):
    return {r["task_id"]: r for r in json.loads(Path("output", name).read_text())}


def test_callback_statuses_exact(client):
    r = run(client)
    assert r.status_code == 200, r.text
    assert {t: x["callback"] for t, x in by_id().items()} == {
        "P01": "delivered", "P02": "delivered", "P03": "delivered", "P04": "failed", "P05": "skipped",
        "P06": "failed", "P07": "delivered", "P08": "skipped", "P09": "skipped", "P10": "skipped"}


def test_callback_errors(client):
    got = run(client).json()["errors"]
    assert keyed(got, {"callback_failed"}) == [("tasks", 4, "P04", "callback_failed"),
                                               ("tasks", 6, "P06", "callback_failed")]


@pytest.mark.parametrize("tid,calls", [
    ("P01", 1),   # 200
    ("P02", 2),   # 500 then 200
    ("P03", 2),   # timeout then 200
    ("P04", 1),   # 400: not retried
    ("P06", 3),   # 503 forever: 1 try + 2 retries
    ("P07", 1),   # 202 counts as delivered
    ("P05", 0),   # no final label -> skipped, no call
    ("P10", 0),
])
def test_callback_call_counts(client, hooks, tid, calls):
    assert run(client).status_code == 200
    assert hooks.count(tid) == calls


def test_payload_exact(client, hooks):
    run(client)
    bodies = {c["task_id"]: c["body"] for c in hooks.calls}
    assert bodies["P01"] == {"task_id": "P01", "label": "spam", "resolved_by": "consensus"}
    assert bodies["P07"] == {"task_id": "P07", "label": "harassment", "resolved_by": "llm"}


def test_signature_matches_raw_body(client, hooks):
    run(client)
    assert hooks.calls
    for c in hooks.calls:
        want = "sha256=" + hmac.new(CALLBACK_SECRET.encode(), c["raw"], hashlib.sha256).hexdigest()
        assert c["headers"].get("x-signature") == want, c["task_id"]
        assert c["headers"].get("content-type", "").startswith("application/json")


def test_idempotency_key_stable_across_retries(client, hooks):
    run(client)
    for c in hooks.calls:
        assert c["headers"].get("idempotency-key") == c["task_id"]


def test_wrong_secret_fails_without_retry(client, hooks, monkeypatch):
    monkeypatch.setenv("CALLBACK_SECRET", "not-the-secret")
    r = run(client)
    assert r.status_code == 200
    assert hooks.count(None) == 6  # one 401 per task with a final label
    assert sum(e["error"] == "callback_failed" for e in r.json()["errors"]) == 6


@pytest.mark.parametrize("var", ["CALLBACK_URL", "CALLBACK_SECRET"])
def test_missing_config_is_503(client, llm, monkeypatch, var):
    monkeypatch.delenv(var)
    assert run(client).status_code == 503
    assert llm.count(None) == 0
    assert not Path("output/labels.json").exists()


def test_secret_never_leaks(client, caplog, capfd):
    caplog.set_level(logging.DEBUG)
    r = run(client)
    out, err = capfd.readouterr()
    assert CALLBACK_SECRET not in caplog.text + out + err + r.text + Path("output/labels.json").read_text()


# ---------------------------------------------------------------- scale


def large(client):
    return run(client, tasks="data/tasks_large.csv", annotations="data/annotations_large.csv",
               output="output/large.json")


def test_large_order_and_values(client, llm, hooks):
    r = large(client)
    assert r.status_code == 200, r.text
    assert r.json()["tasks_written"] == 200
    with open("data/tasks_large.csv", encoding="utf-8") as f:
        ids = [row["task_id"] for row in csv.DictReader(f)]
    rows = json.loads(Path("output/large.json").read_text())
    assert [x["task_id"] for x in rows] == ids
    for x in rows:
        odd = int(x["task_id"][1:]) % 2
        assert (x["final_label"], x["resolved_by"], x["callback"]) == (
            ("spam", "llm", "delivered") if odd else ("safe", "consensus", "delivered")), x
    assert llm.count(None) == 100 and hooks.count(None) == 200


def test_bounded_parallel_llm(client, llm):
    llm.delay = 0.05
    t0 = time.monotonic()
    assert large(client).status_code == 200
    elapsed = time.monotonic() - t0
    assert llm.peak <= 5, f"{llm.peak} LLM requests in flight at once (max 5)"
    assert llm.peak >= 3, f"only {llm.peak} LLM requests in flight at once: not parallel"
    assert elapsed < 4, f"took {elapsed:.1f}s; sequential would be ~5s of LLM alone"


def test_bounded_parallel_callbacks(client, hooks):
    hooks.delay = 0.05
    t0 = time.monotonic()
    assert large(client).status_code == 200
    elapsed = time.monotonic() - t0
    assert hooks.peak <= 5, f"{hooks.peak} callbacks in flight at once (max 5)"
    assert hooks.peak >= 3, f"only {hooks.peak} callbacks in flight at once: not parallel"
    assert elapsed < 7, f"took {elapsed:.1f}s; sequential would be ~10s"
