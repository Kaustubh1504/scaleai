from lb.registry import WorkerRegistry
from mock_services.clock import FakeClock
from mock_services.workers import MockWorker


def make(*ids):
    clock = FakeClock()
    return [MockWorker(i, clock=clock) for i in ids]


def test_iterates_in_registration_order():
    registry = WorkerRegistry()
    for worker in make("b", "a", "c"):
        registry.register(worker)
    assert [w.worker_id for w in registry] == ["b", "a", "c"]
    assert registry.ids() == ["b", "a", "c"]
    assert len(registry) == 3 and "a" in registry and "z" not in registry


def test_unregister_and_get():
    registry = WorkerRegistry()
    w1, w2 = make("w1", "w2")
    registry.register(w1)
    registry.register(w2)
    registry.unregister("w1")
    assert registry.get("w1") is None and registry.get("w2") is w2
    assert registry.ids() == ["w2"]
