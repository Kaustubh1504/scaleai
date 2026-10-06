"""Starter test: talks to the mock API directly. Add your own tests next to it."""

from mock_services.api import API_KEY, make_api
from mock_services.clock import FakeClock


def test_mock_api_answers():
    api = make_api(clock=FakeClock())
    http = api.client()
    page = http.get("/v1/projects/prj_01/tasks", params={"limit": 25}, headers={"X-API-Key": API_KEY}).json()
    assert len(page["data"]) == 25 and page["next_cursor"]
    assert http.get("/v1/projects/prj_01/tasks").status_code == 401
