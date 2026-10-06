"""Starter test showing how to build the app with a fake clock and a test config.

Add your own tests next to this one.
"""

from fastapi.testclient import TestClient

from app.main import create_app
from mock_services.clock import FakeClock

CONFIG = {
    "plans": {"free": {"burst": 5, "refill_per_s": 1.0}, "pro": {"burst": 20, "refill_per_s": 10.0}},
    "tenants": {"acme": {"plan": "pro"}, "globex": {"plan": "free"}},
}


def test_health(tmp_path):
    clock = FakeClock()
    client = TestClient(create_app(storage_dir=tmp_path, clock=clock, tenants=CONFIG))
    assert client.get("/health").json() == {"status": "ok"}
