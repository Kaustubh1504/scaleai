"""Starter test: talks to the mock API directly. Add your own tests next to it."""

from mock_services.api import CLIENT_ID, CLIENT_SECRET, make_api
from mock_services.clock import FakeClock


def test_mock_api_answers():
    api = make_api(clock=FakeClock())
    http = api.client()
    token = http.post("/oauth/token", json={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}).json()
    page = http.get("/v1/projects", headers={"Authorization": f"Bearer {token['access_token']}"}).json()
    assert page["page"] == 1 and page["results"]
