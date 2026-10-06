"""Unit tests: config parsing, body fingerprint, token bucket arithmetic."""

import pytest
from pydantic import ValidationError

from app.config import Plan, parse_config
from app.models import TaskIn, valid_idempotency_key
from app.ratelimit import RateLimiter
from mock_services.clock import FakeClock


def test_fingerprint_ignores_key_order_and_defaults():
    a = TaskIn.model_validate_json('{"project": "p", "payload": {"b": 1, "a": {"y": 2, "x": 3}}}')
    b = TaskIn.model_validate_json('{"payload": {"a": {"x": 3, "y": 2}, "b": 1}, "priority": 5, "project": "p"}')
    assert a.fingerprint() == b.fingerprint()
    assert a.fingerprint() != TaskIn(project="p", payload={}, priority=4).fingerprint()


@pytest.mark.parametrize("raw", ['{"project": "p", "payload": {}, "priority": "3"}',
                                 '{"project": "p", "payload": {}, "priority": 3.0}',
                                 '{"project": "p", "payload": {}, "priority": false}',
                                 '{"project": "", "payload": {}}',
                                 '{"project": "p", "payload": {}, "extra": 1}'])
def test_strict_validation(raw):
    with pytest.raises(ValidationError):
        TaskIn.model_validate_json(raw)


@pytest.mark.parametrize("key, ok", [("a", True), ("A_b-9" * 12 + "abcd", True), ("x" * 65, False),
                                     ("", False), ("a b", False), ("a\n", False)])
def test_idempotency_key_format(key, ok):
    assert valid_idempotency_key(key) is ok


def test_config_rejects_unknown_plan_and_bad_numbers():
    with pytest.raises(ValueError):
        parse_config({"plans": {"free": {"burst": 5, "refill_per_s": 1}}, "tenants": {"t": {"plan": "gold"}}})
    with pytest.raises(ValueError):
        parse_config({"plans": {"free": {"burst": 5, "refill_per_s": 0}}, "tenants": {}})
    cfg = parse_config({"plans": {"free": {"burst": 5, "refill_per_s": 1}}, "tenants": {"t": {"plan": "free"}}})
    assert cfg.plan_for("t") == Plan(5.0, 1.0) and cfg.plan_for("nope") is None


def test_bucket_drains_refills_and_caps():
    clock = FakeClock()
    limiter, plan = RateLimiter(clock), Plan(burst=2, refill_per_s=0.25)
    assert [limiter.try_acquire("t", plan).remaining for _ in range(2)] == [1, 0]
    denied = limiter.try_acquire("t", plan)
    assert (denied.allowed, denied.retry_after, denied.remaining) == (False, 4, 0)
    clock.advance(3.5)
    assert limiter.try_acquire("t", plan).retry_after == 1
    clock.advance(0.5)
    assert limiter.try_acquire("t", plan).allowed
    clock.advance(10_000)
    assert limiter.remaining("t", plan) == 2
    assert limiter.remaining("other", plan) == 2


def test_float_noise_does_not_break_rounding():
    clock = FakeClock(start=0)
    limiter, plan = RateLimiter(clock), Plan(burst=10, refill_per_s=10)
    for _ in range(10):
        limiter.try_acquire("t", plan)
    for _ in range(3):
        clock.advance(0.1)  # 0.1 * 3 * 10 is 3.0000000000000004 in floats
    assert limiter.remaining("t", plan) == 3
    assert [limiter.try_acquire("t", plan).allowed for _ in range(4)] == [True, True, True, False]
