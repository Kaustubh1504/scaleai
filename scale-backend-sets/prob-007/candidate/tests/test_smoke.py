"""Starter tests: how to build a pool with fake workers and a fake clock.

Add your own tests next to these.
"""

import pytest

from mock_services.clock import FakeClock
from mock_services.workers import MockWorker
from pool.coordinator import Pool
from pool.demo import load_jobs


def test_builds_with_fakes():
    clock = FakeClock()
    pool = Pool([], clock, concurrency_per_worker=1, job_timeout_s=1.0)
    assert pool.clock is clock and pool.concurrency_per_worker == 1
    worker = MockWorker("w1", clock=clock)
    assert worker.process({"id": "j1"}, timeout=1.0) == {"task_id": "j1", "worker_id": "w1", "status": "done"}


@pytest.mark.parametrize("kwargs", [{"concurrency_per_worker": 0}, {"job_timeout_s": 0}, {"heartbeat_timeout_s": -1},
                                    {"max_attempts": 0}, {"backoff_base_s": -0.5}])
def test_rejects_bad_settings(kwargs):
    with pytest.raises(ValueError):
        Pool([], FakeClock(), **kwargs)


def test_load_jobs_skips_malformed_lines(tmp_path):
    path = tmp_path / "jobs.jsonl"
    path.write_text('{"id": "a"}\n\nnot json\n{"id": 7}\n{"id": ""}\n["b"]\n{"id": "c", "payload": {"k": 1}}\n')
    assert load_jobs(path) == [("a", {"id": "a"}), ("c", {"k": 1})]
