"""Shared builders for the reference tests."""

from lb.balancer import LoadBalancer
from lb.models import Task
from mock_services.clock import FakeClock
from mock_services.workers import MockWorker, default_handler

T0 = 1000.0


def handler(worker_id, payload):
    if isinstance(payload, dict) and payload.get("poison"):
        raise ValueError("poison")
    return default_handler(worker_id, payload)


def setup(*ids, **lb_kwargs):
    clock = FakeClock(start=T0)
    workers = [MockWorker(i, clock=clock, handler=handler) for i in ids]
    lb = LoadBalancer(clock, **lb_kwargs)
    for w in workers:
        lb.add_worker(w)
    return lb, clock, workers


def task(task_id, priority=0, **payload):
    return Task(id=task_id, priority=priority, payload={"id": task_id, **payload})


def served(lb, n, prefix="t"):
    return [lb.dispatch(task(f"{prefix}{i}")).worker_id for i in range(n)]
