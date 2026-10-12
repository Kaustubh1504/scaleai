"""Mock Vendor Batches API for problem 13. Tests and your __main__ block both use make_api().

The vendor's server clock runs ``server_skew_s`` ahead of yours, and every response
carries a ``Date`` header from *its* clock.
"""

from __future__ import annotations

from email.utils import formatdate
from typing import Callable

from kit import Call, FakeClock, MockAPI, error_response, json_response


def make_batches(n: int) -> dict[str, dict]:
    states = ("queued", "labeling", "review", "delivered")
    return {f"bat_{i:03d}": {"id": f"bat_{i:03d}", "state": states[i % 4], "tasks": 50 * i}
            for i in range(1, n + 1)}


def make_api(clock: FakeClock, *, n_batches: int = 10, server_skew_s: float = 3600.0) -> MockAPI:
    """
    GET /v1/batches/{batch_id} -> the batch, or 404; 403 for "bat_locked".

    429 helpers (use them in api.script):
      api.too_many(retry_after)  -> 429 with ``Retry-After: <retry_after>`` (None = no header)
      api.too_many_in(seconds)   -> 429 whose Retry-After is an HTTP-date ``seconds`` after the server's Date
    The kit's own "429:N" / "429" outcomes work too (they carry no Date header).
    """
    api = MockAPI(clock=clock)
    batches = make_batches(n_batches)
    api.batches = batches

    def server_date(offset_s: float = 0.0) -> str:
        return formatdate(clock.time() + server_skew_s + offset_s, usegmt=True)

    @api.route("GET", "/v1/batches/{batch_id}")
    def get_batch(req, batch_id):
        if batch_id == "bat_locked":
            return error_response(403, "forbidden", {"Date": server_date()})
        if batch_id not in batches:
            return error_response(404, f"batch {batch_id} not found", {"Date": server_date()})
        return json_response(batches[batch_id], headers={"Date": server_date()})

    def too_many(retry_after: str | None) -> Callable[[Call], object]:
        def outcome(call: Call):
            headers = {"Date": server_date()}
            if retry_after is not None:
                headers["Retry-After"] = retry_after
            return error_response(429, "slow down", headers)
        return outcome

    def too_many_in(seconds: float) -> Callable[[Call], object]:
        def outcome(call: Call):
            return error_response(429, "slow down", {"Date": server_date(), "Retry-After": server_date(seconds)})
        return outcome

    api.too_many = too_many
    api.too_many_in = too_many_in
    return api
