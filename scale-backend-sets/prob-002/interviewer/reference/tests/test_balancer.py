"""Starter tests: how to build a balancer with fake workers and a fake clock.

Add your own tests next to these.
"""

import pytest

from lb.balancer import LoadBalancer, NoWorkersAvailable
from lb.models import Task
from mock_services.clock import FakeClock
from mock_services.workers import MockWorker


def test_round_robin_over_healthy_workers():
    clock = FakeClock()
    balancer = LoadBalancer(clock)
    for i in (1, 2, 3):
        balancer.add_worker(MockWorker(f"w{i}", clock=clock))
    results = [balancer.dispatch(Task(id=f"t{n}", payload={"id": f"t{n}"})) for n in range(4)]
    assert [r.worker_id for r in results] == ["w1", "w2", "w3", "w1"]
    assert results[0].result == {"task_id": "t0", "worker_id": "w1", "status": "done"}
    assert results[0].attempts == 1


def test_no_workers():
    with pytest.raises(NoWorkersAvailable):
        LoadBalancer(FakeClock()).dispatch(Task(id="t1"))


@pytest.mark.parametrize("kwargs", [{"task_timeout_s": 0}, {"heartbeat_timeout_s": -1}, {"max_attempts": 0}])
def test_rejects_bad_settings(kwargs):
    with pytest.raises(ValueError):
        LoadBalancer(FakeClock(), **kwargs)
