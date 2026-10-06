"""The Tasks API you are exporting from, running in-process.

    from mock_services.api import API_KEY, make_api
    api = make_api()                 # same data every time (seed 9)
    http = api.client()              # an httpx.Client wired to the mock (no sockets)
    http.get("/v1/projects/prj_01/tasks", params={"limit": 25}, headers={"X-API-Key": API_KEY})

Read API.md for the endpoints. Useful knobs while testing your code:

    from shared.mock_rest import FaultConfig, RateLimitConfig
    make_api(faults=FaultConfig(scripted={"GET /v1/projects/prj_02/tasks?cursor": [503, "429:3", "malformed"]}))
    make_api(faults=FaultConfig(failure_rate=0.2, malformed_rate=0.05))   # random, but reproducible
    make_api(rate_limit=RateLimitConfig(requests=4, window_s=10))          # a strict limit
    make_api(latency_s=1.0)                                                # every request takes 1 s of clock time
    make_api(on_request=lambda api, request: ...)                          # run code before each request
    api.log                     # every request the mock received: method, path, params, status, at, outcome
    api.rendered("tasks")       # every task exactly as the API serves it

Scripted outcomes apply to successive requests whose "METHOD /path?sorted-query"
contains the key: an int status, "429:<seconds>", "timeout", "malformed"
(a 200 with a truncated body) or "ok". The first page of a project has no
cursor ("...tasks?limit=25"); later pages do ("...tasks?cursor=...&limit=25").

Run it as a real server instead (optional):
    python -m mock_services.api_server --port 9300
"""

from __future__ import annotations

from typing import Callable

import mock_services  # noqa: F401  (puts shared/ on sys.path)
from shared.fake_clock import Clock
from shared.mock_rest import AuthConfig, FaultConfig, MockRestAPI, RateLimitConfig, scale_resources

API_KEY = "key_live_exporter"


def make_resources(seed: int, *, projects: int = 8, tasks: int = 400):
    resources = scale_resources(seed, projects=projects, tasks=tasks, annotators=10, submissions_per_task=(0, 0))
    by_name = {r.name: r for r in resources}
    by_name["tasks"].default_page_size, by_name["tasks"].max_page_size = 10, 25
    return [by_name["projects"], by_name["tasks"]]


def make_api(seed: int = 9, clock: Clock | None = None, *, latency_s: float = 0.0, faults: FaultConfig | None = None,
             rate_limit: RateLimitConfig | None = None, projects: int = 8, tasks: int = 400,
             on_request: Callable | None = None, api_key: str = API_KEY) -> MockRestAPI:
    faults = faults or FaultConfig(seed=seed)
    faults.latency_s = faults.latency_s or latency_s
    return MockRestAPI(make_resources(seed, projects=projects, tasks=tasks), clock=clock, faults=faults,
                       rate_limit=rate_limit, on_request=on_request, auth=AuthConfig(mode="api_key", api_key=api_key))
