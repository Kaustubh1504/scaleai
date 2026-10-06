"""Acceptance tests for prob-002.

Run against the candidate's code:
    SOLUTION_DIR=/path/to/candidate python -m pytest interviewer/hidden_tests
Skip the mid-part requirement change if you did not deliver it:
    ... -m "not change"
Without SOLUTION_DIR the tests run against interviewer/reference.

Workers come straight from shared.mock_worker (not the candidate's
mock_services), so candidate edits there cannot change the outcome.
"""

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SOLUTION_DIR = Path(os.environ.get("SOLUTION_DIR", HERE.parent / "reference")).resolve()
sys.path.insert(0, str(SOLUTION_DIR))

import mock_services  # noqa: E402,F401  (puts shared/ on sys.path)

from shared.fake_clock import FakeClock  # noqa: E402
from shared.mock_worker import MockWorker, default_handler  # noqa: E402

T0 = 1000.0  # every test starts its FakeClock here


def pytest_report_header(config):
    return f"solution under test: {SOLUTION_DIR}"


def pytest_configure(config):
    config.addinivalue_line("markers", "change: the mid-part requirement change (deselect with -m 'not change')")


def poison_handler(worker_id, payload):
    """Like the default handler, but a payload with "poison": true raises (-> TaskFailedError)."""
    if isinstance(payload, dict) and payload.get("poison"):
        raise ValueError("poison payload")
    return default_handler(worker_id, payload)


def task(task_id, priority=0, **payload):
    from lb.models import Task

    return Task(id=task_id, priority=priority, payload={"id": task_id, **payload})


def hb(worker_id, in_flight=0, capacity=4, ts=0.0):
    return {"worker_id": worker_id, "in_flight": in_flight, "capacity": capacity, "ts": ts}


def served_by(lb, n, prefix="t"):
    return [lb.dispatch(task(f"{prefix}{i}")).worker_id for i in range(n)]


@pytest.fixture
def clock():
    return FakeClock(start=T0)


@pytest.fixture
def make_workers(clock):
    def build(*ids, **kwargs):
        return [MockWorker(i, clock=clock, handler=poison_handler, **kwargs) for i in ids]

    return build


@pytest.fixture
def make_lb(clock):
    from lb.balancer import LoadBalancer

    def build(*workers, **kwargs):
        lb = LoadBalancer(clock, **kwargs)
        for worker in workers:
            lb.add_worker(worker)
        return lb

    return build
