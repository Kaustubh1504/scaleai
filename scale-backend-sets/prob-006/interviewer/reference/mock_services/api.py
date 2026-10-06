"""The Projects API you are integrating with, running in-process.

    from mock_services.api import make_api
    api = make_api()                 # same data every time (seed 6)
    http = api.client()              # an httpx.Client wired to the mock (no sockets)
    http.post("/oauth/token", json={"client_id": "client", "client_secret": "secret"})

Read API.md for the endpoints. Useful knobs while testing your code:

    from shared.mock_rest import FaultConfig, RateLimitConfig
    make_api(token_ttl_s=10, latency_s=1.0)          # every request takes 1 s of clock time
    make_api(faults=FaultConfig(scripted={"GET /v1/projects?page=2": [503, "429:3"]}))
    make_api(rate_limit=RateLimitConfig(requests=5, window_s=10, retry_after_format="http-date"))
    api.expire_all_tokens(); api.log            # every request the mock received

Run it as a real server instead (optional):
    python -m mock_services.api_server --port 9300
"""

from __future__ import annotations

import mock_services  # noqa: F401  (puts shared/ on sys.path)
from shared.fake_clock import Clock
from shared.mock_rest import AuthConfig, FaultConfig, MockRestAPI, RateLimitConfig, scale_resources

CLIENT_ID = "client"
CLIENT_SECRET = "secret"


def make_resources(seed: int):
    resources = scale_resources(seed, messy=False, projects=12, tasks=600, annotators=10,
                                submissions_per_task=(0, 0))
    by_name = {r.name: r for r in resources}
    by_name["projects"].default_page_size = by_name["projects"].max_page_size = 10
    by_name["tasks"].default_page_size, by_name["tasks"].max_page_size = 10, 25
    return [by_name["projects"], by_name["tasks"]]


def make_api(seed: int = 6, clock: Clock | None = None, *, token_ttl_s: float = 300.0, latency_s: float = 0.0,
             faults: FaultConfig | None = None, rate_limit: RateLimitConfig | None = None) -> MockRestAPI:
    faults = faults or FaultConfig(seed=seed)
    faults.latency_s = faults.latency_s or latency_s
    return MockRestAPI(make_resources(seed), clock=clock, faults=faults, rate_limit=rate_limit,
                       auth=AuthConfig(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_ttl_s=token_ttl_s))
