"""Part 3: backoff, dead letters, poison jobs and drain."""

import pytest

from helpers import T0, setup, submit, worker_of


def test_backoff_schedule_and_eligibility():
    pool, clock, _ = setup("w1", heartbeat_timeout_s=100)
    submit(pool, "f", fail_times=2)
    pool.tick()
    assert pool.pending() == ["f"] and pool.job("f")["status"] == "queued"
    for at, sends in [(T0 + 0.999, 0), (T0 + 1, 1), (T0 + 2.999, 0), (T0 + 3, 1)]:
        clock.set(at)
        assert pool.tick() == sends
    assert pool.job("f")["status"] == "done" and pool.job("f")["attempts"] == 3
    assert clock.sleeps == []


def test_retry_goes_to_the_back_and_does_not_block_others():
    pool, _, _ = setup("w1", concurrency_per_worker=1, heartbeat_timeout_s=100)
    submit(pool, "f", fail=True)
    submit(pool, "a")
    pool.tick()
    assert pool.pending() == ["a", "f"]
    pool.tick()
    submit(pool, "c")
    assert pool.tick() == 1 and pool.pending() == ["f"]


def test_max_attempts_dead_letters_with_history():
    pool, clock, _ = setup("w1", "w2", backoff_base_s=0)
    submit(pool, "bad", fail=True)
    pool.run_until_idle()
    job = pool.job("bad")
    assert job["status"] == "failed" and job["error"] and job["attempts"] == 3
    (letter,) = pool.dead_letters
    assert letter["job_id"] == "bad" and letter["reason"] == "max_attempts"
    assert letter["payload"] == {"id": "bad", "fail": True}
    assert [h["worker_id"] for h in letter["history"]] == ["w1", "w2", "w1"]
    assert all(h["error"] and h["at"] == T0 for h in letter["history"])
    pool.dead_letters.clear()
    pool.dead_letters[0]["history"].clear()
    assert len(pool.dead_letters[0]["history"]) == 3


def test_worker_losses_do_not_use_up_attempts_or_backoff():
    pool, _, (w1, w2) = setup("w1", "w2", max_attempts=1, backoff_base_s=100)
    w1.crash_on_next()
    submit(pool, "a")
    pool.tick()
    pool.tick()
    assert pool.job("a")["status"] == "done" and worker_of(pool, "a") == ["w2"]
    assert pool.dead_letters == []


def test_poison_job_is_dead_lettered_after_two_workers():
    pool, _, (w1, w2, w3) = setup("w1", "w2", "w3")
    submit(pool, "p", crash=True)
    pool.tick()
    pool.tick()
    assert pool.job("p")["status"] == "failed" and pool.pending() == []
    (letter,) = pool.dead_letters
    assert letter["reason"] == "poison" and [h["worker_id"] for h in letter["history"]] == ["w1", "w2"]
    assert w3.received == []
    submit(pool, "ok")
    pool.tick()
    assert worker_of(pool, "ok") == ["w3"]


def test_lost_twice_on_the_same_worker_is_not_poison():
    pool, _, (w1,) = setup("w1")
    w1.latency_s = 0.5
    w1.slow(10)  # 5 s per job: always over the 2 s timeout, but it keeps heartbeating
    submit(pool, "a")
    for _ in range(2):
        pool.tick()
        pool.on_heartbeat(w1.heartbeat())
    assert pool.job("a")["attempts"] == 2 and pool.pending() == ["a"] and pool.dead_letters == []


def test_drain_runs_what_it_can_and_closes_intake():
    pool, _, _ = setup("w1", "w2")
    submit(pool, "f", fail_times=1)
    submit(pool, "a", "b")
    assert pool.drain() == ["f"]  # waiting for its backoff; drain does not wait
    assert pool.status()["done"] == 2
    with pytest.raises(RuntimeError):
        pool.submit("new", {})
    with pytest.raises(RuntimeError):
        pool.submit("a", {"id": "a"})
    assert pool.drain() == ["f"]
