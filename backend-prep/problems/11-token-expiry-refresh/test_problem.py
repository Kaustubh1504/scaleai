from urllib.parse import parse_qsl

import pytest

from problem_api import CLIENT_ID, CLIENT_SECRET, make_api


def make_client(sol, api, clock, secret=CLIENT_SECRET):
    return sol.ApiClient(api.client(), CLIENT_ID, secret, clock)


def crawl(client, n=60, start=1):
    return [client.get(f"/v1/tasks/task_{i:04d}") for i in range(start, start + n)]


def token_calls(api):
    return api.calls("POST", "/oauth/token")


def grants(api):
    return [dict(parse_qsl(c.body.decode())).get("grant_type") for c in token_calls(api)]


def data_calls(api):
    return [c for c in api.log if c.path.startswith("/v1/")]


def assert_no_expired_tokens(api):
    for c in data_calls(api):
        auth = c.header("authorization") or ""
        tok = auth.removeprefix("Bearer ")
        assert tok in api.issued, f"{c.key} at t={c.at} sent an unknown token {auth!r}"
        issued_at, expires_at = api.issued[tok]
        assert c.at < expires_at, (
            f"{c.key} reached the server at t={c.at - 1_700_000_000:.0f}s with a token that expired "
            f"at t={expires_at - 1_700_000_000:.0f}s; refresh before expiry, not after a 401")


def test_crawl_returns_tasks(sol, clock):
    """A 60-request crawl returns every task in order"""
    api = make_api(clock)
    tasks = crawl(make_client(sol, api, clock))
    assert [t["id"] for t in tasks] == [t["id"] for t in api.tasks]


def test_lazy_and_form_encoded(sol, clock):
    """No request in __init__; the first token request is a form-encoded client_credentials grant"""
    api = make_api(clock)
    client = make_client(sol, api, clock)
    assert api.log == [], "the constructor must not make requests"
    client.get("/v1/tasks/task_0001")
    first = token_calls(api)[0]
    assert first.status == 200, "token request failed: form-encode it (data=) and send client_id/client_secret"
    assert dict(parse_qsl(first.body.decode())) == {
        "grant_type": "client_credentials", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
    assert data_calls(api)[0].header("authorization") == "Bearer tok_00001"


def test_never_sends_expired_token(sol, clock):
    """Across the crawl, no request reaches the server with an expired token (zero 401s)"""
    api = make_api(clock)
    crawl(make_client(sol, api, clock))
    assert_no_expired_tokens(api)
    assert not [c for c in api.log if c.status == 401], "a 401 means you waited for the server to reject the token"


def test_minimal_token_requests(sol, clock):
    """Refreshes only when the token expires in < 2 s: 8 token requests for 60 GETs"""
    api = make_api(clock)
    crawl(make_client(sol, api, clock))
    n = len(token_calls(api))
    assert n == 8, (f"made {n} token requests; expected 8 (token at t, GETs at t+1..t+8, refresh at t+9). "
                    "Measure expiry from clock.time() just before the token request")


def test_uses_refresh_token_grant(sol, clock):
    """After the first token, renewals use grant_type=refresh_token with the latest refresh token"""
    api = make_api(clock)
    crawl(make_client(sol, api, clock), n=20)
    g = grants(api)
    assert g[0] == "client_credentials"
    assert len(g) > 1 and all(x == "refresh_token" for x in g[1:]), f"grant types used: {g}"
    assert all(c.status == 200 for c in token_calls(api)), "refresh tokens are single-use: send the newest one"


def test_clock_jump_refreshes_proactively(sol, clock):
    """After an idle gap longer than the TTL, the next call refreshes first instead of eating a 401"""
    api = make_api(clock)
    client = make_client(sol, api, clock)
    client.get("/v1/tasks/task_0001")
    clock.advance(300)
    client.get("/v1/tasks/task_0002")
    assert_no_expired_tokens(api)
    assert len(data_calls(api)) == 2, "the second GET should go out once, with a fresh token"


def test_revoked_mid_crawl_recovers(sol, clock):
    """Tokens revoked mid-crawl: one 401, one new token, the same request retried once"""
    api = make_api(clock)
    client = make_client(sol, api, clock)
    crawl(client, n=4)
    before = len(token_calls(api))
    api.issuer.revoke_all()
    task = client.get("/v1/tasks/task_0005", params={"verbose": "1"})
    assert task["id"] == "task_0005"
    tail = data_calls(api)[-2:]
    assert [c.status for c in tail] == [401, 200], f"expected 401 then a successful retry, got {[c.status for c in tail]}"
    assert tail[0].path == tail[1].path and tail[0].params == tail[1].params, "retry the same request (path and params)"
    assert len(token_calls(api)) == before + 1, "exactly one new token after the 401"
    crawl(client, n=10, start=6)
    assert len([c for c in api.log if c.status == 401]) == 1, "only the revoked token should ever be rejected"


def test_double_401_raises(sol, clock):
    """A 401 on the retry too raises AuthError after exactly two attempts"""
    api = make_api(clock)
    api.script("GET /v1/tasks/task_0001", [401, 401])
    with pytest.raises(sol.AuthError) as exc:
        make_client(sol, api, clock).get("/v1/tasks/task_0001")
    assert exc.value.status == 401
    assert len(data_calls(api)) == 2, f"made {len(data_calls(api))} attempts; retry once, then give up"


def test_refresh_falls_back_to_client_credentials(sol, clock):
    """A refresh grant that returns 400 falls back to client_credentials and the crawl continues"""
    api = make_api(clock, refresh_broken=True)
    tasks = crawl(make_client(sol, api, clock), n=20)
    assert len(tasks) == 20
    g = grants(api)
    assert g[:3] == ["client_credentials", "refresh_token", "client_credentials"], f"grant types used: {g}"
    assert_no_expired_tokens(api)


def test_bad_credentials_raise_auth_error(sol, clock):
    """Wrong client credentials (401 from /oauth/token) raise AuthError without calling the API"""
    api = make_api(clock)
    with pytest.raises(sol.AuthError):
        make_client(sol, api, clock, secret="wrong").get("/v1/tasks/task_0001")
    assert data_calls(api) == [], "don't send a data request without a token"


def test_params_and_other_errors(sol, clock):
    """Passes params through; a 404 raises ApiError(404), not AuthError, with no retry"""
    api = make_api(clock)
    client = make_client(sol, api, clock)
    page = client.get("/v1/tasks", params={"page": 2, "per_page": 5})
    assert [t["id"] for t in page["data"]] == [f"task_{i:04d}" for i in range(6, 11)]
    with pytest.raises(sol.ApiError) as exc:
        client.get("/v1/tasks/task_9999")
    assert exc.value.status == 404 and not isinstance(exc.value, sol.AuthError)
    assert len(api.calls("GET", "/v1/tasks/task_9999")) == 1
