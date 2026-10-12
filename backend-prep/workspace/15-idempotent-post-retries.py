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
    return f"pay:{order_id}"


def pay(client: httpx.Client, order_id: str, amount_cents: int, *, clock: Any, rng: random.Random,
        max_attempts: int = 5, base_s: float = 0.5, cap_s: float = 8.0) -> dict:
    path = "/v1/payments"
    body = {"order_id":order_id, "amount_cents":amount_cents}
    headers = {"Idempotency-Key": idempotency_key(order_id)}
    reason = ""
    
    for attempt in range(1, max_attempts+1):
        try:
            resp = client.post(path, json=body, headers=headers)
        except httpx.TransportError as exc:
            status, reason = None, exc
        else:
            status = resp.status_code
            if resp.is_success:
                try:
                    return resp.json()
                except ValueError:
                    reason = "invalid json"
                    
            elif status == 409:
                raise IdempotencyConflictError(status, order_id, resp.text[:200])
            
            elif status in TRANSIENT_STATUSES:
                reason = resp.text[:200]
                
            else:
                raise PaymentError(status, order_id, resp.text[:200])
        
        
        if attempt < max_attempts:
            d = min(cap_s, base_s * 2 ** (attempt - 1))
            clock.sleep(rng.uniform(d / 2, d))

        
    raise PaymentError(status, order_id, f"gave up after {max_attempts} attempts: {reason}")
            
    


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
