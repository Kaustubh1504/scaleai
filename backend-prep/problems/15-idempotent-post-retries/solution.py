"""15. Idempotent POST retries: reference solution."""

from __future__ import annotations

import random
from typing import Any

import httpx


class PaymentError(Exception):
    def __init__(self, status: int | None, order_id: str, message: str = ""):
        super().__init__(f"payment for {order_id} failed ({status}): {message}")
        self.status = status
        self.order_id = order_id


class IdempotencyConflictError(PaymentError):
    pass


def pay(client: httpx.Client, order_id: str, amount_cents: int, *, clock: Any, rng: random.Random,
        max_attempts: int = 5, base_s: float = 0.5, cap_s: float = 8.0) -> dict:
    headers = {"Idempotency-Key": f"pay:{order_id}"}
    body = {"order_id": order_id, "amount_cents": amount_cents}
    for attempt in range(1, max_attempts + 1):
        try:
            resp = client.post("/v1/payments", json=body, headers=headers)
        except httpx.TransportError:
            status = None  # the server may have charged; retrying with the same key is safe
        else:
            status = resp.status_code
            if resp.is_success:
                try:
                    return resp.json()
                except ValueError:
                    pass
            elif status == 409:
                raise IdempotencyConflictError(status, order_id, resp.text)
            elif status not in (500, 502, 503, 504):
                raise PaymentError(status, order_id, resp.text)
        if attempt < max_attempts:
            d = min(cap_s, base_s * 2 ** (attempt - 1))
            clock.sleep(rng.uniform(d / 2, d))
    raise PaymentError(status, order_id, f"gave up after {max_attempts} attempts")


if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import make_api

    api = make_api()
    api.script("POST /v1/payments", [api.timeout_after_commit, "malformed", 503])
    clock = FakeClock()
    print(pay(api.client(), "ord_1001", 2599, clock=clock, rng=random.Random(0)))
    print("payments stored:", list(api.payments.values()))
    print("re-run:", pay(api.client(), "ord_1001", 2599, clock=clock, rng=random.Random(0)))
