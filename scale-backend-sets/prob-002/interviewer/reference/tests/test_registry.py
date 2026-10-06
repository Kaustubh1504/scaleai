import pytest


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


def test_duplicate_id_is_rejected_and_original_kept():
    registry = WorkerRegistry()
    first, = make("w1")
    registry.register(first)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(MockWorker("w1", clock=FakeClock()))
    assert registry.get("w1") is first


def test_unregister_unknown_is_key_error_and_re_register_goes_last():
    registry = WorkerRegistry()
    w1, w2 = make("w1", "w2")
    registry.register(w1)
    registry.register(w2)
    with pytest.raises(KeyError):
        registry.unregister("nope")
    assert registry.unregister("w1") is w1
    registry.register(w1)
    assert registry.ids() == ["w2", "w1"]
