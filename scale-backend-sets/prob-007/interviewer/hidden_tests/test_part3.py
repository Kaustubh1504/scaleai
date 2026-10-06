"""Part 3: retries with backoff, dead letters, poison jobs, drain."""

import pytest

from conftest import T0, load_fixture_jobs, states, submit_all, worker_of
from shared.mock_worker import MockWorker, WorkerFleet

LONG = 1_000.0  # heartbeat timeout for tests that move the clock but are not about liveness


# ------------------------------------------------------------------ backoff

def test_failed_attempt_is_retried_after_backoff(make_pool, make_workers, clock):
    pool = make_pool(*make_workers("w1"), heartbeat_timeout_s=LONG)
    submit_all(pool, "f", fail_times=2)
    assert pool.tick() == 1
    job = pool.job("f")
    assert job["status"] == "queued" and job["attempts"] == 1 and job["error"] is None
    assert pool.pending() == ["f"]
    for at, sends in [(T0, 0), (T0 + 0.999, 0), (T0 + 1.0, 1), (T0 + 2.999, 0), (T0 + 3.0, 1)]:
        clock.set(at)
        assert pool.tick() == sends, at
    assert pool.job("f")["status"] == "done" and pool.job("f")["attempts"] == 3
    assert pool.dead_letters == []
    assert clock.sleeps == []


def test_backoff_is_measured_from_after_the_failed_call(make_pool, clock):
    from conftest import make_handler

    w1 = MockWorker("w1", latency_s=0.5, clock=clock, handler=make_handler())
    pool = make_pool(w1, heartbeat_timeout_s=LONG, backoff_base_s=2.0)
    submit_all(pool, "f", fail_times=1)
    pool.tick()  # the failed call ends at T0 + 0.5
    clock.set(T0 + 2.49)
    assert pool.tick() == 0
    clock.set(T0 + 2.5)
    assert pool.tick() == 1 and pool.job("f")["status"] == "done"


def test_custom_backoff_base_doubles(make_pool, make_workers, clock):
    pool = make_pool(*make_workers("w1"), heartbeat_timeout_s=LONG, backoff_base_s=0.5, max_attempts=4)
    submit_all(pool, "f", fail_times=3)
    times = []
    while pool.job("f")["status"] == "queued":
        if pool.tick():
            times.append(clock.time() - T0)
        clock.advance(0.25)
    assert times == [0.0, 0.5, 1.5, 3.5]  # waits of 0.5, 1, 2


def test_zero_backoff_retries_next_round(make_pool, make_workers):
    pool = make_pool(*make_workers("w1"), backoff_base_s=0)
    submit_all(pool, "f", fail_times=2)
    assert [pool.tick() for _ in range(3)] == [1, 1, 1]
    assert pool.job("f")["status"] == "done"


def test_retry_goes_to_the_back_of_the_queue(make_pool, make_workers):
    pool = make_pool(*make_workers("w1"), concurrency_per_worker=1, backoff_base_s=0)
    submit_all(pool, "f", fail_times=1)
    submit_all(pool, "a", "b")
    pool.tick()
    assert pool.pending() == ["a", "b", "f"]


def test_waiting_job_keeps_its_place_and_does_not_block(make_pool, make_workers, clock):
    (w1,) = make_workers("w1")
    pool = make_pool(w1, concurrency_per_worker=1, heartbeat_timeout_s=LONG)
    submit_all(pool, "f", fail_times=1)
    submit_all(pool, "a")
    pool.tick()
    pool.tick()
    submit_all(pool, "c", "d")
    assert pool.pending() == ["f", "c", "d"]
    assert pool.tick() == 1
    assert pool.pending() == ["f", "d"] and pool.job("c")["status"] == "done"
    clock.set(T0 + 1)
    pool.tick()
    assert pool.job("f")["status"] == "done" and pool.pending() == ["d"]


def test_failures_count_across_workers(make_pool, make_workers):
    pool = make_pool(*make_workers("w1", "w2"), backoff_base_s=0)
    submit_all(pool, "f", fail_times=2)
    pool.run_until_idle()
    assert pool.job("f")["status"] == "done" and pool.job("f")["attempts"] == 3
    assert worker_of(pool, "f") == ["w1"]  # w1, w2, w1 by the least-loaded rule


# ------------------------------------------------------------------ dead letters

def test_max_attempts_dead_letters_the_job(make_pool, make_workers, clock):
    pool = make_pool(*make_workers("w1", "w2"), heartbeat_timeout_s=LONG)
    submit_all(pool, "bad", fail=True)
    pool.tick()
    clock.set(T0 + 1)
    pool.tick()
    assert pool.dead_letters == []
    clock.set(T0 + 3)
    pool.tick()
    job = pool.job("bad")
    assert job["status"] == "failed" and isinstance(job["error"], str) and job["error"]
    assert job["attempts"] == 3 and pool.pending() == []
    assert pool.dead_letters == [{
        "job_id": "bad",
        "payload": {"id": "bad", "fail": True},
        "reason": "max_attempts",
        "history": [
            {"worker_id": "w1", "error": pool.dead_letters[0]["history"][0]["error"], "at": T0},
            {"worker_id": "w2", "error": pool.dead_letters[0]["history"][1]["error"], "at": T0 + 1},
            {"worker_id": "w1", "error": pool.dead_letters[0]["history"][2]["error"], "at": T0 + 3},
        ],
    }]
    assert all(isinstance(h["error"], str) and h["error"] for h in pool.dead_letters[0]["history"])
    assert pool.status()["failed"] == 1


@pytest.mark.parametrize("max_attempts", [1, 2, 5])
def test_custom_max_attempts(make_pool, make_workers, max_attempts):
    pool = make_pool(*make_workers("w1"), max_attempts=max_attempts, backoff_base_s=0)
    submit_all(pool, "bad", fail=True)
    pool.run_until_idle()
    assert pool.job("bad")["attempts"] == max_attempts
    assert len(pool.dead_letters[0]["history"]) == max_attempts


def test_dead_letters_in_order_and_returned_as_copies(make_pool, make_workers):
    pool = make_pool(*make_workers("w1"), max_attempts=1, concurrency_per_worker=1)
    submit_all(pool, "x", fail=True)
    submit_all(pool, "y", fail=True)
    pool.run_until_idle()
    letters = pool.dead_letters
    assert [d["job_id"] for d in letters] == ["x", "y"]
    letters[0]["history"].clear()
    letters[0]["payload"]["fail"] = False
    letters.clear()
    again = pool.dead_letters
    assert len(again) == 2 and len(again[0]["history"]) == 1 and again[0]["payload"] == {"id": "x", "fail": True}


def test_history_includes_worker_errors_before_the_failures(make_pool, make_workers):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2, max_attempts=1, backoff_base_s=0)
    w1.crash_on_next()
    submit_all(pool, "bad", fail=True)
    pool.tick()
    pool.tick()
    (letter,) = pool.dead_letters
    assert letter["reason"] == "max_attempts"
    assert [h["worker_id"] for h in letter["history"]] == ["w1", "w2"]


# ------------------------------------------------------------------ worker errors are not failures

def test_worker_loss_does_not_use_up_attempts_or_wait(make_pool, make_workers):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2, max_attempts=1, backoff_base_s=100)
    w1.crash_on_next()
    submit_all(pool, "a")
    pool.tick()
    assert pool.pending() == ["a"] and pool.job("a")["status"] == "queued"
    assert pool.tick() == 1
    assert pool.job("a")["status"] == "done" and pool.dead_letters == []


def test_overload_refusals_are_not_failures(make_pool, make_workers):
    (w1,) = make_workers("w1")
    pool = make_pool(w1, max_attempts=1)
    w1.in_flight = w1.capacity
    submit_all(pool, "a")
    for _ in range(3):
        pool.tick()
    assert pool.job("a")["status"] == "queued" and pool.job("a")["attempts"] == 3
    w1.in_flight = 0
    pool.tick()
    assert pool.job("a")["status"] == "done" and pool.dead_letters == []


# ------------------------------------------------------------------ poison jobs

def test_poison_job_dead_lettered_after_killing_two_workers(make_pool, make_workers):
    w1, w2, w3 = make_workers("w1", "w2", "w3")
    pool = make_pool(w1, w2, w3)
    submit_all(pool, "p", crash=True)
    pool.tick()
    assert pool.pending() == ["p"] and states(pool)["w1"] == "down"
    pool.tick()
    job = pool.job("p")
    assert job["status"] == "failed" and job["error"] and job["attempts"] == 2
    assert pool.pending() == [] and w3.received == []
    (letter,) = pool.dead_letters
    assert letter["job_id"] == "p" and letter["reason"] == "poison"
    assert letter["payload"] == {"id": "p", "crash": True}
    assert [h["worker_id"] for h in letter["history"]] == ["w1", "w2"]
    assert states(pool) == {"w1": "down", "w2": "down", "w3": "up"}
    submit_all(pool, "ok")
    pool.tick()
    assert worker_of(pool, "ok") == ["w3"]


def test_poison_ignores_failure_count(make_pool, make_workers):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2, max_attempts=10)
    w1.go_silent()
    w2.kill()
    submit_all(pool, "p")
    pool.tick()
    assert pool.pending() == ["p"]
    pool.tick()
    assert pool.dead_letters[0]["reason"] == "poison" and pool.job("p")["status"] == "failed"


def test_lost_twice_on_same_worker_is_not_poison(make_pool, clock):
    slow = MockWorker("w1", latency_s=1.0, clock=clock)
    pool = make_pool(slow, job_timeout_s=2.0)
    slow.slow(5)  # always over the timeout, but still heartbeating
    submit_all(pool, "a")
    for _ in range(3):
        pool.tick()
        pool.on_heartbeat(slow.heartbeat())
    assert pool.job("a")["status"] == "queued" and pool.job("a")["attempts"] == 3
    assert pool.dead_letters == [] and pool.pending() == ["a"]


def test_other_jobs_on_the_poisoned_workers_are_not_blamed(make_pool, make_workers):
    w1, w2, w3 = make_workers("w1", "w2", "w3")
    pool = make_pool(w1, w2, w3, concurrency_per_worker=2)
    submit_all(pool, "p", crash=True)
    submit_all(pool, "x", "y", "z")
    pool.tick()  # p->w1 (crash), x->w2, y->w3, z->w1 (not sent)
    pool.tick()  # p->w2 (crash: poison), z->w3
    assert pool.dead_letters[0]["job_id"] == "p" and len(pool.dead_letters) == 1
    assert {j: pool.job(j)["status"] for j in "xyz"} == {"x": "done", "y": "done", "z": "done"}


# ------------------------------------------------------------------ drain

def test_drain_runs_what_it_can_and_returns_the_rest(make_pool, make_workers):
    pool = make_pool(*make_workers("w1", "w2"), concurrency_per_worker=1)
    submit_all(pool, "f", fail_times=1)
    submit_all(pool, "a", "b", "c")
    left = pool.drain()
    assert left == ["f"]  # waiting for its backoff; drain does not wait
    assert [pool.job(j)["status"] for j in "abc"] == ["done"] * 3
    assert pool.job("f")["status"] == "queued" and pool.dead_letters == []


def test_drain_closes_intake(make_pool, make_workers):
    pool = make_pool(*make_workers("w1"))
    submit_all(pool, "a")
    assert pool.drain() == []
    with pytest.raises(RuntimeError):
        pool.submit("new", {"id": "new"})
    with pytest.raises(RuntimeError):
        pool.submit("a", {"id": "a"})
    assert pool.pending() == [] and pool.status()["done"] == 1


def test_drain_with_fleet_down_hands_back_jobs_in_order(make_pool, make_workers):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2)
    w1.kill()
    w2.kill()
    submit_all(pool, "a", "b", "c")
    assert pool.drain() == ["a", "b", "c"]
    w1.revive()
    pool.on_heartbeat(w1.heartbeat())
    assert pool.tick() == 2  # still usable after drain
    assert pool.pending() == ["c"]


def test_drain_respects_max_ticks(make_pool, make_workers):
    pool = make_pool(*make_workers("w1"), concurrency_per_worker=1)
    submit_all(pool, *"abcd")
    assert pool.drain(max_ticks=2) == ["c", "d"]


def test_never_sleeps(make_pool, make_workers, clock):
    workers = make_workers("w1", "w2")
    pool = make_pool(*workers)
    submit_all(pool, "f", fail_times=2)
    submit_all(pool, "bad", fail=True)
    for _ in range(10):
        WorkerFleet(workers, clock=clock).run(1, sink=pool.on_heartbeat)
        pool.tick()
    assert clock.sleeps == []
    assert pool.job("f")["status"] == "done" and pool.job("bad")["status"] == "failed"


# ------------------------------------------------------------------ end to end

def test_sample_file_end_to_end(make_pool, make_workers, clock):
    workers = make_workers("w1", "w2", "w3")
    pool = make_pool(*workers)
    fleet = WorkerFleet(workers, clock=clock)
    for job_id, payload in load_fixture_jobs():
        try:
            pool.submit(job_id, payload)
        except ValueError:
            pass
    for _ in range(12):
        for w in workers:
            if w.heartbeat() is None:
                w.revive()  # the supervisor restarts crashed workers
        fleet.run(1, sink=pool.on_heartbeat)
        pool.tick()
    assert pool.pending() == []
    assert {d["job_id"]: d["reason"] for d in pool.dead_letters} == {"poison-001": "poison",
                                                                     "broken-001": "max_attempts"}
    assert set(pool.results) == {"resize-001", "resize-002", "transcode-001", "flaky-001", "thumb-001",
                                 "export-001", "thumb-003"}
    assert pool.job("flaky-001")["attempts"] == 3
