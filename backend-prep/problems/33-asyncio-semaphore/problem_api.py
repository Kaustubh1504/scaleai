"""Mock Model Responses API for problem 33. Tests and your __main__ block both use make_api().

Requests made through ``api.async_client()`` really ``await asyncio.sleep``
(between 0.4x and 1.6x ``latency_s``, depending on the id), so responses finish
out of order and ``api.max_in_flight`` shows how many overlapped.
"""

from __future__ import annotations

import asyncio

import httpx

from kit import MockAPI, error_response

MODELS = ("model-a", "model-b")


def response_id(i: int) -> str:
    return f"resp_{i:04d}"


def make_response(i: int) -> dict:
    return {
        "id": response_id(i),
        "prompt_id": f"prm_{(i + 1) // 2:04d}",
        "model": MODELS[i % 2],
        "text": f"Answer #{i}",
        "tokens": 40 + (i * 13) % 60,
    }


class JitteredAPI(MockAPI):
    """MockAPI whose async latency depends on the request path (so completion order != send order)."""

    def __init__(self, latency_s: float):
        super().__init__()
        self.latency_s_avg = latency_s

    def _delay(self, path: str) -> float:
        tail = path.rsplit("_", 1)[-1]
        n = int(tail) if tail.isdigit() else 0
        return self.latency_s_avg * (1 + (n * 7) % 4) / 2.5

    async def _handle_async(self, request: httpx.Request) -> httpx.Response:
        self._enter()
        try:
            await asyncio.sleep(self._delay(request.url.path))
            return self._dispatch(request)
        finally:
            self._leave()


def make_api(n_responses: int = 100, *, latency_s: float = 0.02) -> MockAPI:
    """
    n_responses : resp_0001 .. resp_<n> exist; any other id is a 404.
    latency_s   : average real time per request (async client only).
    """
    api = JitteredAPI(latency_s)
    records = {response_id(i): make_response(i) for i in range(1, n_responses + 1)}
    api.records = records

    @api.route("GET", "/v1/responses/{rid}")
    def get_response(req, rid):
        if rid not in records:
            return error_response(404, f"response {rid} not found")
        return dict(records[rid])

    return api
