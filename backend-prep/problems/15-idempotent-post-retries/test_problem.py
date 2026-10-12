import random

import pytest

from problem_api import make_api

KEY = "POST /v1/payments"


def pay(sol, api, clock, order_id="ord_1001", amount=2599, **kwargs):
    return sol.pay(api.client(), order_id, amount, clock=clock, rng=random.Random(0), **kwargs)


def posts(api):
    return api.calls("POST", "/v1/payments")


def test_happy_path(sol, clock):
    """One clean POST returns the payment and sends Idempotency-Key: pay:<order_id>"""
    api = make_api()
    payment = pay(sol, api, clock)
    assert payment == {"id": "pay_0001", "order_id": "ord_1001", "amount_cents": 2599, "status": "succeeded"}
    calls = posts(api)
    assert len(calls) == 1
    assert calls[0].header("idempotency-key") == "pay:ord_1001", \
        f"key must be derived from the order id, got {calls[0].header('idempotency-key')!r}"
    assert calls[0].json() == {"order_id": "ord_1001", "amount_cents": 2599}
    assert clock.sleeps == []


def test_garbage_body_after_commit_charges_once(sol, clock):
    """A truncated 201 (server stored it) is retried with the same key: one payment, the stored one returned"""
    api = make_api()
    api.script(KEY, ["malformed"])
    payment = pay(sol, api, clock)
    assert len(api.payments) == 1, f"customer charged {len(api.payments)} times"
    assert payment == api.payments["pay_0001"]
    assert len(posts(api)) == 2
    assert posts(api)[1].status == 200, "the retry should be answered by an idempotent replay"


def test_timeout_after_commit_charges_once(sol, clock):
    """A timeout after the server stored the payment is retried safely: exactly one payment"""
    api = make_api()
    api.script(KEY, [api.timeout_after_commit])
    payment = pay(sol, api, clock)
    assert len(api.payments) == 1, f"customer charged {len(api.payments)} times"
    assert payment["id"] == "pay_0001"
    assert len(posts(api)) == 2
    assert len(clock.sleeps) == 1, "back off once between the two attempts"


def test_mixed_faults_charge_once(sol, clock):
    """503, timeout, timeout-after-commit, malformed and connect error in a row still charge once"""
    api = make_api()
    api.script(KEY, [503, "timeout", api.timeout_after_commit, "malformed", "connect"])
    payment = pay(sol, api, clock, max_attempts=6)
    assert len(api.payments) == 1, f"customer charged {len(api.payments)} times"
    assert payment["amount_cents"] == 2599
    assert len(posts(api)) == 6
    assert len(clock.sleeps) == 5


def test_retries_reuse_key_and_body(sol, clock):
    """Every retry sends the same Idempotency-Key and an identical body"""
    api = make_api()
    api.script(KEY, [502, "timeout", "connect"])
    pay(sol, api, clock, order_id="ord_7", amount=100)
    calls = posts(api)
    assert len(calls) == 4
    assert {c.header("idempotency-key") for c in calls} == {"pay:ord_7"}, "a new key per retry defeats the point"
    assert all(c.json() == {"order_id": "ord_7", "amount_cents": 100} for c in calls), \
        "a different body under the same key is a 409"


def test_rerun_returns_same_payment(sol, clock):
    """Running pay() again for the same order (a script re-run) returns the same payment, not a new one"""
    api = make_api()
    first = pay(sol, api, clock)
    second = pay(sol, api, clock)
    assert second == first
    assert len(api.payments) == 1, "a re-run must not charge again"
    assert posts(api)[1].status == 200


def test_different_orders_different_keys(sol, clock):
    """Two orders get two keys and two payments"""
    api = make_api()
    a = pay(sol, api, clock, order_id="ord_A", amount=500)
    b = pay(sol, api, clock, order_id="ord_B", amount=500)
    assert a["id"] != b["id"]
    assert len(api.payments) == 2, "same amount, different orders: both must be paid"
    assert [c.header("idempotency-key") for c in posts(api)] == ["pay:ord_A", "pay:ord_B"]


def test_conflict_raises(sol, clock):
    """Same order with a different amount gets a 409: IdempotencyConflictError, not retried"""
    api = make_api()
    pay(sol, api, clock, amount=1000)
    with pytest.raises(sol.IdempotencyConflictError) as exc:
        pay(sol, api, clock, amount=2000)
    assert exc.value.status == 409
    assert exc.value.order_id == "ord_1001"
    assert len(posts(api)) == 2, "a 409 is not transient: one request, no retry"
    assert len(api.payments) == 1


def test_validation_error_not_retried(sol, clock):
    """A 422 (amount_cents=0) raises PaymentError(422) at once, not IdempotencyConflictError"""
    api = make_api()
    with pytest.raises(sol.PaymentError) as exc:
        pay(sol, api, clock, amount=0)
    assert exc.value.status == 422
    assert not isinstance(exc.value, sol.IdempotencyConflictError)
    assert len(posts(api)) == 1
    assert clock.sleeps == []


def test_gives_up_after_max_attempts(sol, clock):
    """Five 503s raise PaymentError(503) after 4 backoff sleeps, and nothing is charged"""
    api = make_api()
    api.script(KEY, [503] * 5)
    with pytest.raises(sol.PaymentError) as exc:
        pay(sol, api, clock)
    assert exc.value.status == 503
    assert len(posts(api)) == 5
    assert len(clock.sleeps) == 4, "no sleep after the last attempt"
    assert api.payments == {}
