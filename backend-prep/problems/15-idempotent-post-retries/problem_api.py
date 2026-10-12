"""Mock Payouts/Payments API for problem 15. Tests and your __main__ block both use make_api().

POST /v1/payments is idempotent on the ``Idempotency-Key`` header, like Stripe's API.
"""

from __future__ import annotations

import json

import httpx

from kit import Call, MockAPI, error_response, json_response


def make_api(clock=None) -> MockAPI:
    """
    POST /v1/payments  {"order_id": str, "amount_cents": int > 0}, header Idempotency-Key required
        new key                       -> 201 {"id", "order_id", "amount_cents", "status"}
        same key, same body           -> 200, the stored payment, header Idempotent-Replayed: true
        same key, different body      -> 409
        no key -> 400, bad body -> 422
    GET  /v1/payments/{payment_id}    -> the payment, or 404

    api.payments        : dict payment_id -> payment (what was really charged)
    api.timeout_after_commit : a script outcome that stores the payment, then raises httpx.ReadTimeout
                               (the server did the work; you never saw the answer)
    """
    api = MockAPI(clock=clock)
    payments: dict[str, dict] = {}
    by_key: dict[str, tuple[str, dict]] = {}  # key -> (canonical request body, stored payment)
    api.payments = payments

    def create_payment(call: Call) -> httpx.Response:
        key = call.header("idempotency-key")
        if not key:
            return error_response(400, "Idempotency-Key header is required")
        try:
            body = call.json()
        except ValueError:
            return error_response(400, "body must be JSON")
        if not isinstance(body, dict):
            return error_response(422, "body must be an object")
        order_id, amount = body.get("order_id"), body.get("amount_cents")
        if not isinstance(order_id, str) or not order_id:
            return error_response(422, "order_id is required")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            return error_response(422, "amount_cents must be a positive integer")

        canonical = json.dumps(body, sort_keys=True)
        if key in by_key:
            stored_body, payment = by_key[key]
            if stored_body != canonical:
                return error_response(409, "Idempotency-Key was already used with a different request body")
            return json_response(payment, 200, {"Idempotent-Replayed": "true"})

        payment = {"id": f"pay_{len(payments) + 1:04d}", "order_id": order_id,
                   "amount_cents": amount, "status": "succeeded"}
        payments[payment["id"]] = payment
        by_key[key] = (canonical, payment)
        return json_response(payment, 201)

    def get_payment(call: Call, payment_id: str):
        if payment_id not in payments:
            return error_response(404, f"payment {payment_id} not found")
        return payments[payment_id]

    def timeout_after_commit(call: Call):
        create_payment(call)  # the side effect happens...
        raise httpx.ReadTimeout("mock: read timed out (after the server stored the payment)")  # ...you never hear back

    api.add_route("POST", "/v1/payments", create_payment)
    api.add_route("GET", "/v1/payments/{payment_id}", get_payment)
    api.timeout_after_commit = timeout_after_commit
    return api
