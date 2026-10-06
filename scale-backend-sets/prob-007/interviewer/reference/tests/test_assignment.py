"""Part 1: submit, the plan/run round, least-loaded assignment and inspection."""

import pytest

from helpers import setup, submit, worker_of
from mock_services.workers import MockWorker
from pool.coordinator import Pool


def test_round_follows_least_loaded_rule_from_the_spec_example():
    pool, _, _ = setup("w1", "w2")
    submit(pool, "a", "b", "c", "d", "e")
    assert pool.tick() == 4
    assert worker_of(pool, "a", "b", "c", "d") == ["w1", "w2", "w1", "w2"]
    assert pool.pending() == ["e"]
    assert pool.tick() == 1 and worker_of(pool, "e") == ["w1"]
    submit(pool, "f")
    pool.tick()
    assert worker_of(pool, "f") == ["w2"]
    assert pool.tick() == 0


def test_job_view_results_and_status():
    pool, _, _ = setup("w1")
    submit(pool, "a")
    assert pool.job("a") == {"id": "a", "status": "queued", "attempts": 0, "worker_id": None,
                             "result": None, "error": None}
    pool.tick()
    expected = {"task_id": "a", "worker_id": "w1", "status": "done"}
    assert pool.job("a") == {"id": "a", "status": "done", "attempts": 1, "worker_id": "w1",
                             "result": expected, "error": None}
    assert pool.results == {"a": expected}
    assert pool.status() == {"queued": 0, "done": 1, "failed": 0, "workers": {"w1": "up"}}
    pool.results.clear()
    pool.job("a")["result"]["status"] = "mutated"
    assert pool.results == {"a": expected}
    with pytest.raises(KeyError):
        pool.job("nope")


def test_task_failure_fails_the_job_and_worker_stays_up():
    pool, _, _ = setup("w1", max_attempts=1)
    submit(pool, "bad", fail=True)
    submit(pool, "good")
    pool.tick()
    bad = pool.job("bad")
    assert bad["status"] == "failed" and bad["error"] and bad["result"] is None
    assert pool.job("good")["status"] == "done"
    assert pool.status()["workers"] == {"w1": "up"} and pool.pending() == []


def test_submit_is_idempotent_by_id():
    pool, _, _ = setup("w1")
    payload = {"id": "a", "n": [1]}
    assert pool.submit("a", payload) is True
    payload["n"].append(2)  # the caller's later edits do not reach the job
    assert pool.submit("a", {"id": "a", "n": [1]}) is False
    with pytest.raises(ValueError):
        pool.submit("a", {"id": "a", "n": [9]})
    pool.tick()
    assert pool.submit("a", {"id": "a", "n": [1]}) is False  # done jobs keep their id
    assert pool.pending() == [] and pool.job("a")["attempts"] == 1
    for bad in ("", None, 7):
        with pytest.raises(ValueError):
            pool.submit(bad, {})


def test_slot_limit_and_run_until_idle():
    pool, _, (w1,) = setup("w1", concurrency_per_worker=1)
    submit(pool, "a", "b", "c")
    assert pool.run_until_idle(max_ticks=2) == 2
    assert pool.pending() == ["c"]
    assert pool.run_until_idle() == 1
    assert [p["id"] for p in w1.received] == ["a", "b", "c"]


def test_payload_and_timeout_are_passed_through():
    class Recorder:
        worker_id = "r1"

        def __init__(self):
            self.calls = []

        def process(self, payload, timeout=None):
            self.calls.append((payload, timeout))
            return "ok"

        def heartbeat(self):
            return None

    rec = Recorder()
    pool = Pool([rec], job_timeout_s=1.5)
    pool.submit("x", {"k": 1})
    pool.submit("y")
    pool.tick()
    assert rec.calls == [({"k": 1}, 1.5), (None, 1.5)]


def test_duplicate_worker_ids_and_no_workers():
    with pytest.raises(ValueError):
        Pool([MockWorker("w1"), MockWorker("w1")])
    pool = Pool([])
    pool.submit("a")
    assert pool.tick() == 0 and pool.pending() == ["a"]
    assert pool.status() == {"queued": 1, "done": 0, "failed": 0, "workers": {}}
