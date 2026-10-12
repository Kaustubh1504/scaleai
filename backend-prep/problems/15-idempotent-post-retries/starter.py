"""15. Idempotent POST retries

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import random
from typing import Any
import httpx

TRANSIENT_STATUSES = frozenset({500, 502, 503, 504})


class PaymentError(Exception):
    def __init__(self, status: int | None, order_id: str, message: str = ""):
        super().__init__(f"payment for {order_id} failed ({status}): {message}")
        self.status = status
        self.order_id = order_id


class IdempotencyConflictError(PaymentError):
    """409: this order's key was already used for a different amount."""


def idempotency_key(order_id: str) -> str:
    # Derived from the order, not random: a re-run of the whole script reuses it too.
    raise NotImplementedError


def pay(client: httpx.Client, order_id: str, amount_cents: int, *, clock: Any, rng: random.Random,
        max_attempts: int = 5, base_s: float = 0.5, cap_s: float = 8.0) -> dict:
    raise NotImplementedError


if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import make_api

    api = make_api()
    api.script("POST /v1/payments", [api.timeout_after_commit, "malformed", 503])
    clock = FakeClock()
    payment = pay(api.client(), "ord_1001", 2599, clock=clock, rng=random.Random(0))
    print(payment, "after", len(api.log), "requests")
    print("payments stored:", list(api.payments.values()))
    print("re-run:", pay(api.client(), "ord_1001", 2599, clock=clock, rng=random.Random(0)))
