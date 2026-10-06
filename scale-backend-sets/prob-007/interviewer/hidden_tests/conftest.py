"""Acceptance tests for prob-007.

Run against the candidate's code:
    SOLUTION_DIR=/path/to/candidate python -m pytest interviewer/hidden_tests
Skip the mid-part requirement change if you did not deliver it:
    ... -m "not change"
Without SOLUTION_DIR the tests run against interviewer/reference.

Workers come straight from shared.mock_worker (not the candidate's
mock_services), so candidate edits there cannot change the outcome. Every
test is single-threaded on a FakeClock.
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SOLUTION_DIR = Path(os.environ.get("SOLUTION_DIR", HERE.parent / "reference")).resolve()
FIXTURES = HERE / "fixtures"
sys.path.insert(0, str(SOLUTION_DIR))

import mock_services  # noqa: E402,F401  (puts shared/ on sys.path)

from shared.fake_clock import FakeClock  # noqa: E402
from shared.mock_worker import MockWorker, default_handler  # noqa: E402

T0 = 1000.0  # every test starts its FakeClock here


def pytest_report_header(config):
    return f"solution under test: {SOLUTION_DIR}"


def pytest_configure(config):
    config.addinivalue_line("markers", "change: the mid-part requirement change (deselect with -m 'not change')")


class CrashingWorker(MockWorker):
    """Copy of mock_services.workers.CrashingWorker: dies mid-job on a payload with "crash": true."""

    def process(self, task, timeout=None):
        if isinstance(task, dict) and task.get("crash"):
            self.crash_on_next()
        return super().process(task, timeout)


def make_handler():
    """payload "fail": true always raises (-> TaskFailedError); "fail_times": n raises on the first n attempts."""
    seen = Counter()

    def handler(worker_id, payload):
        if isinstance(payload, dict):
            seen[payload.get("id")] += 1
            if payload.get("fail") or seen[payload.get("id")] <= payload.get("fail_times", 0):
                raise ValueError("job blew up")
        return default_handler(worker_id, payload)

    return handler


def load_fixture_jobs(name="jobs.jsonl"):
    """An independent parser for the fixture: (id, payload) of each well-formed line."""
    jobs = []
    for line in (FIXTURES / name).read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and isinstance(row.get("id"), str) and row["id"]:
            jobs.append((row["id"], row.get("payload", {"id": row["id"]})))
    return jobs


def done_by(worker_id, job_id):
    return {"task_id": job_id, "worker_id": worker_id, "status": "done"}


def submit_all(pool, *ids, **extra):
    for job_id in ids:
        assert pool.submit(job_id, {"id": job_id, **extra}) is True


def worker_of(pool, *ids):
    return [pool.job(i)["worker_id"] for i in ids]


def states(pool):
    return pool.status()["workers"]


@pytest.fixture
def clock():
    return FakeClock(start=T0)


@pytest.fixture
def make_workers(clock):
    handler = make_handler()

    def build(*ids, **kwargs):
        return [CrashingWorker(i, clock=clock, handler=handler, **kwargs) for i in ids]

    return build


@pytest.fixture
def make_pool(clock):
    from pool.coordinator import Pool

    def build(*workers, **kwargs):
        return Pool(list(workers), clock, **kwargs)

    return build
