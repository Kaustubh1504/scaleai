import asyncio
from email.utils import parsedate_to_datetime

import httpx
import pytest

from shared.fake_clock import FakeClock
from shared.mock_rest import (
    AuthConfig,
    FaultConfig,
    FieldMess,
    MockRestAPI,
    RateLimitConfig,
    ResourceConfig,
    render,
    scale_records,
)


def login(http, **extra):
    resp = http.post("/oauth/token", json={"client_id": "client", "client_secret": "secret", **extra})
    assert resp.status_code == 200, resp.text
    return resp.json()


def authed(api, **kwargs):
    http = api.client(**kwargs)
    http.headers["Authorization"] = f"Bearer {login(http)['access_token']}"
    return http


def items_resource(n=23, **kwargs):
    return ResourceConfig("items", [{"id": f"i{k:03d}", "n": k, "updated_at": f"2024-01-{1 + k % 28:02d}T00:00:00Z"}
                                    for k in range(n)], **kwargs)


# ------------------------------------------------------------------ dataset


def test_dataset_is_deterministic_and_related():
    a, b = scale_records(3), scale_records(3)
    assert a == b and a != scale_records(4)
    project_ids = {p["id"] for p in a["projects"]}
    task_ids = {t["id"] for t in a["tasks"]}
    sub_ids = {s["id"] for s in a["submissions"]}
    assert all(t["project_id"] in project_ids for t in a["tasks"])
    assert all(s["task_id"] in task_ids for s in a["submissions"])
    assert all(r["submission_id"] in sub_ids for r in a["reviews"])
    assert len(a["tasks"]) == 240 and a["submissions"] and a["reviews"]


def test_mess_is_stable_and_canonical_is_clean():
    api = MockRestAPI.scale(seed=5, clock=FakeClock())
    first, second = api.rendered("tasks"), api.rendered("tasks")
    assert first == second
    canonical = api.canonical("tasks")
    assert any(r != c for r, c in zip(first, canonical))
    assert all(isinstance(t["reward_cents"], int) for t in canonical)
    rewards = {type(t.get("reward_cents")) for t in first}
    assert {int, str, type(None)} <= rewards


def test_render_variants():
    record = {"id": 1, "when": "2024-01-02T03:04:05Z", "tags": ["a", "b"], "flag": True,
              "boxes": [{"label": "car"}, {"label": "sign"}], "nested": {"x": 5}}
    rules = [FieldMess("when", ["epoch"], 1.0), FieldMess("tags", ["csv"], 1.0), FieldMess("flag", ["bool_int"], 1.0),
             FieldMess("boxes[].label", ["upper"], 1.0), FieldMess("nested.x", ["missing"], 1.0)]
    out = render(record, rules, seed=0, resource="r", record_id=1)
    assert out == {"id": 1, "when": 1704164645, "tags": "a,b", "flag": 1,
                   "boxes": [{"label": "CAR"}, {"label": "SIGN"}], "nested": {}}
    assert record["tags"] == ["a", "b"]  # not mutated


# ------------------------------------------------------------------ auth


def test_oauth_flow_expiry_and_refresh():
    clock = FakeClock()
    api = MockRestAPI([items_resource()], auth=AuthConfig(token_ttl_s=60), clock=clock)
    http = api.client()
    assert http.get("/v1/items").json() == {"error": "missing_token"}
    tokens = login(http)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert http.get("/v1/items", headers=headers).status_code == 200
    clock.advance(60)
    expired = http.get("/v1/items", headers=headers)
    assert expired.status_code == 401 and expired.json()["error"] == "token_expired"
    assert "WWW-Authenticate" in expired.headers
    refreshed = http.post("/oauth/token", json={"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    again = http.post("/oauth/token", json={"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"]})
    assert again.json()["error"] == "invalid_grant"  # single use
    assert http.get("/v1/items", headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"}).status_code == 200


def test_form_encoded_token_and_bad_credentials():
    api = MockRestAPI([items_resource()])
    http = api.client()
    assert http.post("/oauth/token", data={"client_id": "client", "client_secret": "secret"}).status_code == 200
    assert http.post("/oauth/token", json={"client_id": "client", "client_secret": "nope"}).status_code == 401


def test_token_dies_after_n_requests_and_api_key_mode():
    api = MockRestAPI([items_resource()], auth=AuthConfig(max_requests_per_token=2))
    http = authed(api)
    assert [http.get("/v1/items").status_code for _ in range(3)] == [200, 200, 401]

    api = MockRestAPI([items_resource()], auth=AuthConfig(mode="api_key", api_key="k"))
    assert api.client().get("/v1/items", headers={"X-API-Key": "k"}).status_code == 200
    assert api.client().get("/v1/items", headers={"X-API-Key": "x"}).json()["error"] == "invalid_api_key"


# ------------------------------------------------------------------ pagination


def collect(http, path, style, **params):
    out = []
    if style == "page":
        page = 1
        while True:
            body = http.get(path, params={**params, "page": page}).json()
            out += body["results"]
            if page >= body["total_pages"]:
                return out
            page += 1
    if style == "offset":
        offset = 0
        while True:
            body = http.get(path, params={**params, "offset": offset}).json()
            out += body["items"]
            offset += len(body["items"])
            if offset >= body["total"] or not body["items"]:
                return out
    cursor = None
    while True:
        body = http.get(path, params={**params, **({"cursor": cursor} if cursor else {})}).json()
        out += body["data"]
        cursor = body["next_cursor"]
        if cursor is None:
            return out


@pytest.mark.parametrize("style", ["page", "offset", "cursor"])
def test_pagination_styles_return_everything_once(style):
    api = MockRestAPI([items_resource(pagination=style, default_page_size=5)], auth=AuthConfig(mode="none"))
    got = collect(api.client(), "/v1/items", style)
    assert [r["id"] for r in got] == [f"i{k:03d}" for k in range(23)]


def test_pagination_validation_and_envelope_override():
    api = MockRestAPI([items_resource(pagination="page", envelope={"data": "rows"},
                                      default_page_size=5, max_page_size=10)],
                      auth=AuthConfig(mode="none"))
    http = api.client()
    assert set(http.get("/v1/items").json()) == {"rows", "page", "per_page", "total", "total_pages"}
    assert http.get("/v1/items", params={"per_page": 11}).status_code == 400
    assert http.get("/v1/items", params={"page": 0}).status_code == 400
    assert http.get("/v1/items", params={"page": 99}).json()["rows"] == []


def test_cursor_is_stable_under_inserts_but_offset_is_not():
    def run(style):
        api = MockRestAPI([items_resource(n=10, pagination=style, default_page_size=4)], auth=AuthConfig(mode="none"))
        http = api.client()
        first = http.get("/v1/items").json()
        api.insert("items", {"id": "i000a", "n": -1, "updated_at": "2024-01-01T00:00:00Z"})  # sorts before i001
        if style == "cursor":
            rest = []
            cursor = first["next_cursor"]
            while cursor:
                body = http.get("/v1/items", params={"cursor": cursor}).json()
                rest += body["data"]
                cursor = body["next_cursor"]
            return [r["id"] for r in first["data"] + rest]
        body = http.get("/v1/items", params={"offset": 4}).json()
        return [r["id"] for r in first["items"] + body["items"]]

    cursor_ids = run("cursor")
    assert len(cursor_ids) == len(set(cursor_ids)) == 10  # the insert landed on an already-read page
    offset_ids = run("offset")
    assert len(offset_ids) != len(set(offset_ids))  # i003 is seen twice: realistic offset drift


def test_invalid_cursor_and_filters_and_updated_since():
    api = MockRestAPI([items_resource(filters=("n",))], auth=AuthConfig(mode="none"))
    http = api.client()
    assert http.get("/v1/items", params={"cursor": "garbage"}).status_code == 400
    assert [r["id"] for r in http.get("/v1/items", params={"n": "7"}).json()["data"]] == ["i007"]
    since = http.get("/v1/items", params={"updated_since": "2024-01-20T00:00:00Z", "limit": 100}).json()["data"]
    assert since and all(r["updated_at"] > "2024-01-20T00:00:00Z" for r in since)
    assert http.get("/v1/items", params={"updated_since": "yesterday"}).status_code == 400


def test_nested_routes_and_get_one():
    api = MockRestAPI.scale(seed=1, auth=AuthConfig(mode="none"))
    http = api.client()
    project = api.canonical("projects")[0]["id"]
    nested = collect(http, f"/v1/projects/{project}/tasks", "cursor", limit=100)
    expected = [t["id"] for t in api.canonical("tasks") if t["project_id"] == project]
    assert [t["id"] for t in nested] == expected
    assert http.get("/v1/projects/prj_99/tasks").status_code == 404
    assert http.get("/v1/annotators/ann_001").json()["id"] == "ann_001"
    assert http.get("/v1/annotators/nope").status_code == 404
    assert http.get("/v1/annotators/ann_001/tasks").status_code == 404


# ------------------------------------------------------------------ rate limits and faults


def test_rate_limit_retry_after_seconds_and_http_date():
    clock = FakeClock(start=1_700_000_000)
    api = MockRestAPI([items_resource()], auth=AuthConfig(mode="none"), clock=clock,
                      rate_limit=RateLimitConfig(requests=2, window_s=10))
    http = api.client()
    assert [http.get("/v1/items").status_code for _ in range(2)] == [200, 200]
    limited = http.get("/v1/items")
    assert limited.status_code == 429 and limited.headers["Retry-After"] == "10"
    assert limited.headers["X-RateLimit-Remaining"] == "0"
    clock.advance(10)
    assert http.get("/v1/items").status_code == 200

    api = MockRestAPI([items_resource()], auth=AuthConfig(mode="none"), clock=clock,
                      rate_limit=RateLimitConfig(requests=1, window_s=5, retry_after_format="http-date"))
    http = api.client()
    http.get("/v1/items")
    limited = http.get("/v1/items")
    wait = (parsedate_to_datetime(limited.headers["Retry-After"]) - parsedate_to_datetime(limited.headers["Date"]))
    assert wait.total_seconds() == 5


def test_rate_limit_is_per_client_not_per_token():
    api = MockRestAPI([items_resource()], rate_limit=RateLimitConfig(requests=2, window_s=60))
    http = authed(api)
    http.get("/v1/items"), http.get("/v1/items")
    http.headers["Authorization"] = f"Bearer {login(http)['access_token']}"  # new token, same client
    assert http.get("/v1/items").status_code == 429


def test_random_faults_are_deterministic_and_retries_can_succeed():
    def statuses(seed):
        api = MockRestAPI([items_resource()], auth=AuthConfig(mode="none"),
                          faults=FaultConfig(seed=seed, failure_rate=0.4))
        http = api.client()
        return [http.get("/v1/items").status_code for _ in range(30)]

    assert statuses(1) == statuses(1) != statuses(2)
    assert 200 in statuses(1) and any(s >= 500 for s in statuses(1))


def test_scripted_faults_timeout_and_malformed():
    clock = FakeClock()
    api = MockRestAPI([items_resource(pagination="cursor", default_page_size=5)], auth=AuthConfig(mode="none"),
                      clock=clock, faults=FaultConfig(scripted={"GET /v1/items?cursor": [503, "429:3", "timeout",
                                                                                         "malformed"]}))
    http = api.client(timeout=2.0)
    cursor = http.get("/v1/items").json()["next_cursor"]
    assert http.get("/v1/items", params={"cursor": cursor}).status_code == 503
    limited = http.get("/v1/items", params={"cursor": cursor})
    assert limited.status_code == 429 and limited.headers["Retry-After"] == "3"
    before = clock.time()
    with pytest.raises(httpx.ReadTimeout):
        http.get("/v1/items", params={"cursor": cursor})
    assert clock.time() - before == 2.0 and clock.sleeps == []
    bad = http.get("/v1/items", params={"cursor": cursor})
    assert bad.status_code == 200
    with pytest.raises(ValueError):
        bad.json()
    assert http.get("/v1/items", params={"cursor": cursor}).status_code == 200
    assert [e.outcome for e in api.log][-5:] == ["fault:503", "fault:429", "timeout", "fault:malformed", "ok"]


def test_slow_requests_time_out_only_when_client_timeout_is_short():
    clock = FakeClock()
    api = MockRestAPI([items_resource()], auth=AuthConfig(mode="none"), clock=clock,
                      faults=FaultConfig(latency_s=3.0))
    assert api.client(timeout=5.0).get("/v1/items").status_code == 200
    with pytest.raises(httpx.ReadTimeout):
        api.client(timeout=1.0).get("/v1/items")


# ------------------------------------------------------------------ results sink


def test_results_sink_with_idempotency_and_validation():
    def validator(body):
        return None if isinstance(body.get("answer"), int) else "answer must be an integer"

    api = MockRestAPI([ResourceConfig("results", [], pagination="page", writable=True, validator=validator,
                                      updated_field=None)], auth=AuthConfig(mode="none"))
    http = api.client()
    created = http.post("/v1/results", json={"answer": 42}, headers={"Idempotency-Key": "k1"})
    assert created.status_code == 201
    replay = http.post("/v1/results", json={"answer": 42}, headers={"Idempotency-Key": "k1"})
    assert replay.status_code == 200 and replay.json() == created.json()
    assert http.post("/v1/results", json={"answer": "x"}).status_code == 422
    assert [r["answer"] for r in api.canonical("results")] == [42]


def test_async_client_and_server_app():
    api = MockRestAPI.scale(seed=2, auth=AuthConfig(mode="none"))

    async def main():
        async with api.async_client() as http:
            return (await http.get("/v1/projects")).json()

    assert asyncio.run(main())["total"] == 6

    from fastapi.testclient import TestClient

    server = TestClient(api.app())
    assert server.get("/v1/projects", params={"per_page": 2}).json()["total_pages"] == 3


def test_custom_actions_go_through_auth_and_faults():
    def claim(api, request, params, identity):
        task = next((t for t in api.records("items") if t["id"] == params["id"]), None)
        if task is None:
            return 404, {"error": "not_found"}
        if task.get("claimed_by"):
            return 409, {"error": "already_claimed"}
        task["claimed_by"] = identity
        return 200, task

    api = MockRestAPI([items_resource()], actions={("POST", "/v1/items/{id}/claim"): claim},
                      faults=FaultConfig(scripted={"POST /v1/items/i001/claim": [503]}))
    http = api.client()
    assert http.post("/v1/items/i001/claim").status_code == 401
    http = authed(api)
    assert http.post("/v1/items/i001/claim").status_code == 503
    assert http.post("/v1/items/i001/claim").json()["claimed_by"] == "client"
    assert http.post("/v1/items/i001/claim").status_code == 409
    assert http.post("/v1/items/nope/claim").status_code == 404
    assert api.canonical("items")[1]["claimed_by"] == "client"
