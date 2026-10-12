import httpx
import pytest

from problem_api import USERS, make_api, recording_client


def setup():
    api = make_api()
    return api, recording_client(api)


def test_returns_user(sol):
    """An existing user returns the parsed JSON dict"""
    api, client = setup()
    assert sol.get_user(client, "u_001") == USERS["u_001"]
    assert sol.get_user(client, "ops-admin") == USERS["ops-admin"], "ids may contain '-'"
    assert [c.path for c in api.log] == ["/v1/users/u_001", "/v1/users/ops-admin"]


def test_missing_user_is_none(sol):
    """A 404 returns None instead of raising"""
    api, client = setup()
    assert sol.get_user(client, "u_404") is None, "404 means 'no such user': return None"
    assert len(api.log) == 1


def test_sends_five_second_timeout(sol):
    """Every request passes timeout=5 (the client default is 30)"""
    api, client = setup()
    sol.get_user(client, "u_001")
    sol.get_user(client, "u_404")
    assert len(api.timeouts) == 2
    for t in api.timeouts:
        assert t.get("read") == 5 and t.get("connect") == 5, \
            f"expected a 5 s timeout on the request, got {t} (pass timeout=5 to client.get)"


def test_server_error_raises(sol):
    """A 503 raises UserApiError with status 503 and the request path"""
    api, client = setup()
    api.script("GET /v1/users/u_002", [503])
    with pytest.raises(sol.UserApiError) as exc:
        sol.get_user(client, "u_002")
    assert exc.value.status == 503
    assert exc.value.path == "/v1/users/u_002"


def test_other_client_errors_raise(sol):
    """Non-404 4xx responses (401, 403, 429) raise UserApiError too"""
    api, client = setup()
    api.script("GET /v1/users/u_001", [401, 403, "429:1"])
    for status in (401, 403, 429):
        with pytest.raises(sol.UserApiError) as exc:
            sol.get_user(client, "u_001")
        assert exc.value.status == status, f"expected UserApiError({status}), got {exc.value.status}"


def test_timeout_is_wrapped_and_chained(sol):
    """A read timeout raises UserApiError(status=None) chained from the httpx error"""
    api, client = setup()
    api.script("GET /v1/users/u_001", ["timeout"])
    with pytest.raises(sol.UserApiError) as exc:
        sol.get_user(client, "u_001")
    assert exc.value.status is None, "no response came back, so status must be None"
    assert exc.value.path == "/v1/users/u_001"
    assert isinstance(exc.value.__cause__, httpx.TimeoutException), \
        "use `raise UserApiError(...) from exc` so the original error is kept as __cause__"


def test_connect_error_is_wrapped(sol):
    """A connection error raises UserApiError(status=None) chained from httpx.ConnectError"""
    api, client = setup()
    api.script("GET /v1/users/u_003", ["connect"])
    with pytest.raises(sol.UserApiError) as exc:
        sol.get_user(client, "u_003")
    assert exc.value.status is None
    assert isinstance(exc.value.__cause__, httpx.ConnectError)


def test_rejects_unsafe_ids_without_a_request(sol):
    """Unsafe ids ("../admin", "", "a/b", spaces, "?", too long) raise ValueError before any request"""
    api, client = setup()
    for bad in ["../admin", "", "a/b", "u 1", "u?x=1", "u_001#frag", "%2e%2e", "x" * 65]:
        with pytest.raises(ValueError):
            sol.get_user(client, bad)
            pytest.fail(f"get_user({bad!r}) should raise ValueError")
    assert api.log == [], f"no request may be sent for an invalid id, but saw {[c.path for c in api.log]}"


def test_rejects_non_string_ids(sol):
    """A non-string id (e.g. 7 or None) raises ValueError"""
    api, client = setup()
    for bad in [7, None]:
        with pytest.raises(ValueError):
            sol.get_user(client, bad)
    assert api.log == []


def test_max_length_id_is_allowed(sol):
    """A 64-character id is valid (the request is sent; unknown user -> None)"""
    api, client = setup()
    assert sol.get_user(client, "a" * 64) is None
    assert len(api.log) == 1
