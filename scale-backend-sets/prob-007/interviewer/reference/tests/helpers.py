"""Shared builders for the reference tests."""

from collections import Counter

from mock_services.clock import FakeClock
from mock_services.workers import CrashingWorker, default_handler
from pool.coordinator import Pool

T0 = 1000.0


def make_handler():
    """payload "fail": always raises; "fail_times": n raises on the first n attempts of that payload id."""
    seen = Counter()

    def handler(worker_id, payload):
        if isinstance(payload, dict):
            seen[payload.get("id")] += 1
            if payload.get("fail") or seen[payload.get("id")] <= payload.get("fail_times", 0):
                raise ValueError("boom")
        return default_handler(worker_id, payload)

    return handler


def setup(*ids, **pool_kwargs):
    clock = FakeClock(start=T0)
    handler = make_handler()
    workers = [CrashingWorker(i, clock=clock, handler=handler) for i in ids]
    return Pool(workers, clock, **pool_kwargs), clock, workers


def submit(pool, *ids, **payload):
    for job_id in ids:
        assert pool.submit(job_id, {"id": job_id, **payload}) is True


def worker_of(pool, *ids):
    return [pool.job(i)["worker_id"] for i in ids]
