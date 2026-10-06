"""Part 1: submit, rounds (plan + run), least-loaded assignment, slots, inspection."""

import pytest

from conftest import done_by, load_fixture_jobs, states, submit_all, worker_of
from shared.mock_worker import MockWorker


def test_spec_example_round_by_round(make_pool, make_workers):
    pool = make_pool(*make_workers("w1", "w2"))
    submit_all(pool, "a", "b", "c", "d", "e")
    assert pool.tick() == 4
    assert worker_of(pool, "a", "b", "c", "d") == ["w1", "w2", "w1", "w2"]
    assert pool.pending() == ["e"]
    assert pool.tick() == 1
    assert worker_of(pool, "e") == ["w1"]
    assert pool.pending() == []
    submit_all(pool, "f")
    assert pool.tick() == 1
    assert worker_of(pool, "f") == ["w2"]
    assert pool.tick() == 0


def test_least_loaded_spreads_single_jobs_across_rounds(make_pool, make_workers):
    pool = make_pool(*make_workers("w1", "w2", "w3"))
    served = []
    for i in range(7):
        submit_all(pool, f"j{i}")
        assert pool.tick() == 1
        served += worker_of(pool, f"j{i}")
    assert served == ["w1", "w2", "w3", "w1", "w2", "w3", "w1"]


def test_tie_break_on_earlier_calls_within_a_round(make_pool, make_workers):
    pool = make_pool(*make_workers("w1", "w2", "w3"), concurrency_per_worker=3)
    submit_all(pool, "a")
    pool.tick()  # w1 has had 1 call
    submit_all(pool, "b", "c", "d", "e")
    pool.tick()
    # b: all load 0, w2/w3 have fewer earlier calls -> w2; c: w1/w3 at load 0, w3 fewer calls -> w3;
    # d: only w1 at load 0 -> w1; e: all load 1, w2/w3 fewer calls, w2 registered first -> w2
    assert worker_of(pool, "b", "c", "d", "e") == ["w2", "w3", "w1", "w2"]


def test_concurrency_limits_jobs_per_worker_per_round(make_pool, make_workers):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2, concurrency_per_worker=3)
    submit_all(pool, *[f"j{i}" for i in range(8)])
    assert pool.tick() == 6
    assert pool.pending() == ["j6", "j7"]
    assert len(w1.received) == 3 and len(w2.received) == 3
    assert pool.tick() == 2 and pool.pending() == []


def test_fifo_order_with_one_slot(make_pool, make_workers):
    (w1,) = make_workers("w1")
    pool = make_pool(w1, concurrency_per_worker=1)
    submit_all(pool, "c", "a", "b")
    for expected_pending in (["a", "b"], ["b"], []):
        assert pool.tick() == 1
        assert pool.pending() == expected_pending
    assert [p["id"] for p in w1.received] == ["c", "a", "b"]


def test_job_view_and_results(make_pool, make_workers):
    pool = make_pool(*make_workers("w1", "w2"))
    submit_all(pool, "a", "b")
    assert pool.job("a") == {"id": "a", "status": "queued", "attempts": 0, "worker_id": None,
                             "result": None, "error": None}
    pool.tick()
    assert pool.job("a") == {"id": "a", "status": "done", "attempts": 1, "worker_id": "w1",
                             "result": done_by("w1", "a"), "error": None}
    assert pool.results == {"a": done_by("w1", "a"), "b": done_by("w2", "b")}
    assert list(pool.results) == ["a", "b"]


def test_results_in_completion_order(make_pool, make_workers):
    (w1,) = make_workers("w1")
    pool = make_pool(w1, concurrency_per_worker=1)
    submit_all(pool, "z", "y")
    pool.tick()
    submit_all(pool, "a")
    pool.run_until_idle()
    assert list(pool.results) == ["z", "y", "a"]


def test_inspection_returns_copies(make_pool, make_workers):
    pool = make_pool(*make_workers("w1"))
    submit_all(pool, "a", "b")
    pool.pending().clear()
    pool.job("a")["status"] = "done"
    assert pool.pending() == ["a", "b"] and pool.job("a")["status"] == "queued"
    pool.tick()
    pool.results.clear()
    assert set(pool.results) == {"a", "b"}


def test_unknown_job_is_key_error(make_pool, make_workers):
    pool = make_pool(*make_workers("w1"))
    with pytest.raises(KeyError):
        pool.job("nope")


def test_status_counts_and_workers(make_pool, make_workers):
    pool = make_pool(*make_workers("w2", "w1"), concurrency_per_worker=1, max_attempts=1)
    assert pool.status() == {"queued": 0, "done": 0, "failed": 0, "workers": {"w2": "up", "w1": "up"}}
    assert list(pool.status()["workers"]) == ["w2", "w1"]
    submit_all(pool, "ok1")
    submit_all(pool, "bad", fail=True)
    submit_all(pool, "ok2", "ok3")
    pool.tick()
    assert pool.status() == {"queued": 2, "done": 1, "failed": 1, "workers": {"w2": "up", "w1": "up"}}


def test_task_failure_fails_the_job_only(make_pool, make_workers):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2, max_attempts=1)
    submit_all(pool, "bad", fail=True)
    submit_all(pool, "good")
    assert pool.tick() == 2
    bad = pool.job("bad")
    assert bad["status"] == "failed" and isinstance(bad["error"], str) and bad["error"]
    assert bad["attempts"] == 1 and bad["result"] is None and bad["worker_id"] == "w1"
    assert "bad" not in pool.results and pool.job("good")["status"] == "done"
    assert pool.pending() == [] and states(pool) == {"w1": "up", "w2": "up"}
    submit_all(pool, "next1", "next2")
    pool.tick()
    assert worker_of(pool, "next1", "next2") == ["w1", "w2"]  # w1 still gets work


def test_submit_returns_true_and_does_not_run(make_pool, make_workers):
    (w1,) = make_workers("w1")
    pool = make_pool(w1)
    assert pool.submit("a", {"id": "a"}) is True
    assert pool.submit("b") is True
    assert w1.received == [] and pool.pending() == ["a", "b"]
    pool.tick()
    assert w1.received == [{"id": "a"}, None]


def test_resubmit_same_payload_is_ignored(make_pool, make_workers):
    pool = make_pool(*make_workers("w1"))
    assert pool.submit("a", {"id": "a", "n": 1}) is True
    assert pool.submit("a", {"id": "a", "n": 1}) is False
    assert pool.pending() == ["a"]
    pool.tick()
    assert pool.submit("a", {"id": "a", "n": 1}) is False
    assert pool.pending() == [] and pool.job("a")["attempts"] == 1


def test_resubmit_different_payload_is_value_error(make_pool, make_workers):
    pool = make_pool(*make_workers("w1"), max_attempts=1)
    pool.submit("a", {"id": "a"})
    with pytest.raises(ValueError):
        pool.submit("a", {"id": "a", "other": True})
    assert pool.pending() == ["a"]
    pool.submit("bad", {"id": "bad", "fail": True})
    pool.tick()
    assert pool.job("bad")["status"] == "failed"
    with pytest.raises(ValueError):
        pool.submit("bad", {"id": "bad"})  # never reused, even after failing
    assert pool.submit("bad", {"id": "bad", "fail": True}) is False
    assert pool.pending() == []


@pytest.mark.parametrize("job_id", ["", None, 7, ["a"]])
def test_invalid_job_id_is_value_error(make_pool, make_workers, job_id):
    pool = make_pool(*make_workers("w1"))
    with pytest.raises(ValueError):
        pool.submit(job_id, {})
    assert pool.pending() == []


def test_caller_mutating_payload_does_not_change_job(make_pool, make_workers):
    (w1,) = make_workers("w1")
    pool = make_pool(w1)
    payload = {"id": "a", "items": [1, 2]}
    pool.submit("a", payload)
    payload["items"].append(3)
    payload["id"] = "changed"
    pool.tick()
    assert w1.received == [{"id": "a", "items": [1, 2]}]


def test_payload_and_job_timeout_are_passed(make_pool):
    class Recorder:
        worker_id = "r1"

        def __init__(self):
            self.calls = []

        def process(self, payload, timeout=None):
            self.calls.append((payload, timeout))
            return {"ok": payload}

        def heartbeat(self):
            return None

    rec = Recorder()
    pool = make_pool(rec, job_timeout_s=1.25)
    pool.submit("x", {"k": 1})
    pool.tick()
    assert rec.calls == [({"k": 1}, 1.25)]
    assert pool.results == {"x": {"ok": {"k": 1}}}


def test_duplicate_worker_id_in_constructor(make_pool, clock):
    with pytest.raises(ValueError):
        make_pool(MockWorker("w1", clock=clock), MockWorker("w1", clock=clock))


def test_no_workers_keeps_jobs_queued(make_pool):
    pool = make_pool()
    submit_all(pool, "a", "b")
    assert pool.tick() == 0
    assert pool.pending() == ["a", "b"]
    assert pool.status() == {"queued": 2, "done": 0, "failed": 0, "workers": {}}


def test_run_until_idle_counts_sends_and_respects_max_ticks(make_pool, make_workers):
    pool = make_pool(*make_workers("w1"), concurrency_per_worker=1)
    submit_all(pool, *"abcde")
    assert pool.run_until_idle(max_ticks=2) == 2
    assert pool.pending() == ["c", "d", "e"]
    assert pool.run_until_idle() == 3
    assert pool.run_until_idle() == 0


def test_sample_file_runs_through(make_pool, make_workers, clock):
    pool = make_pool(*make_workers("w1", "w2", "w3"), max_attempts=1)
    accepted = []
    for job_id, payload in load_fixture_jobs():
        payload = {k: v for k, v in payload.items() if k != "crash"} if isinstance(payload, dict) else payload
        try:
            if pool.submit(job_id, payload):
                accepted.append(job_id)
        except ValueError:
            pass
    assert accepted == ["resize-001", "resize-002", "transcode-001", "flaky-001", "poison-001", "broken-001",
                        "thumb-001", "export-001", "thumb-003"]
    pool.run_until_idle()
    assert pool.status()["queued"] == 0
    assert pool.job("broken-001")["status"] == "failed" and pool.job("thumb-001")["status"] == "done"
    assert clock.sleeps == []
