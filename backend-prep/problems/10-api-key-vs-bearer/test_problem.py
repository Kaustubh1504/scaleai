import logging
from urllib.parse import parse_qsl

import pytest

from problem_api import API_KEY, CLIENT_ID, CLIENT_SECRET, ITEMS, ORDERS, make_api


def token_calls(api):
    return api.calls("POST", "/oauth/token")


def test_catalog_get_item(sol):
    """CatalogClient.get_item returns the item and sends X-API-Key"""
    api = make_api()
    item = sol.CatalogClient(api.client(), API_KEY).get_item("SKU-200")
    assert item == ITEMS["SKU-200"]
    assert api.log[-1].header("x-api-key") == API_KEY
    assert api.log[-1].header("authorization") is None, "the catalog uses an API key, not a bearer token"


def test_catalog_errors(sol):
    """Catalog: a wrong key raises AuthError(401); an unknown SKU raises ApiError(404)"""
    api = make_api()
    with pytest.raises(sol.AuthError) as exc:
        sol.CatalogClient(api.client(), "wrong").get_item("SKU-100")
    assert exc.value.status == 401
    with pytest.raises(sol.ApiError) as exc:
        sol.CatalogClient(api.client(), API_KEY).get_item("SKU-999")
    assert exc.value.status == 404
    assert not isinstance(exc.value, sol.AuthError), "a 404 is not an auth failure"


def test_orders_list(sol):
    """OrdersClient.list_orders gets a token and returns the orders"""
    api = make_api()
    assert sol.OrdersClient(api.client(), CLIENT_ID, CLIENT_SECRET).list_orders() == ORDERS


def test_token_request_is_form_encoded(sol):
    """The token request is a form-encoded client_credentials grant"""
    api = make_api()
    sol.OrdersClient(api.client(), CLIENT_ID, CLIENT_SECRET).list_orders()
    calls = token_calls(api)
    assert len(calls) == 1 and calls[0].status == 200, "token request failed: send it with data=, not json="
    form = dict(parse_qsl(calls[0].body.decode()))
    assert form == {"grant_type": "client_credentials", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}


def test_bearer_header(sol):
    """Orders requests carry `Authorization: Bearer <access_token>`"""
    api = make_api()
    sol.OrdersClient(api.client(), CLIENT_ID, CLIENT_SECRET).list_orders()
    get = api.calls("GET", "/v1/orders")[0]
    assert get.header("authorization") == "Bearer tok_00001", f"got {get.header('authorization')!r}"


def test_token_lazy_and_reused(sol):
    """No request in __init__; one token request reused across three list_orders calls"""
    api = make_api()
    client = sol.OrdersClient(api.client(), CLIENT_ID, CLIENT_SECRET)
    assert api.log == [], "the constructor must not make requests (fetch the token lazily)"
    for _ in range(3):
        client.list_orders()
    assert len(token_calls(api)) == 1, f"fetched {len(token_calls(api))} tokens; reuse the first one"
    assert len(api.calls("GET", "/v1/orders")) == 3


def test_bad_credentials_raise_auth_error(sol):
    """A rejected token request (401) raises AuthError without calling /v1/orders"""
    api = make_api()
    with pytest.raises(sol.AuthError):
        sol.OrdersClient(api.client(), CLIENT_ID, "wrong-secret").list_orders()
    assert api.calls("GET", "/v1/orders") == [], "don't call the API without a token"


def test_401_on_orders_raises_auth_error(sol):
    """A 401 from /v1/orders (token revoked) raises AuthError, with no refresh"""
    api = make_api()
    client = sol.OrdersClient(api.client(), CLIENT_ID, CLIENT_SECRET)
    client.list_orders()
    api.issuer.revoke_all()
    with pytest.raises(sol.AuthError) as exc:
        client.list_orders()
    assert exc.value.status == 401
    assert len(token_calls(api)) == 1, "no refresh in this problem"


def test_server_error_is_api_error(sol):
    """A 503 from /v1/orders raises ApiError(503), not AuthError"""
    api = make_api()
    api.script("GET /v1/orders", [503])
    with pytest.raises(sol.ApiError) as exc:
        sol.OrdersClient(api.client(), CLIENT_ID, CLIENT_SECRET).list_orders()
    assert exc.value.status == 503 and not isinstance(exc.value, sol.AuthError)


def test_secrets_never_leak(sol, capsys, caplog):
    """repr/str, logs and stdout never contain the API key, client secret or access token"""
    caplog.set_level(logging.DEBUG)
    api = make_api()
    http = api.client()
    catalog = sol.CatalogClient(http, API_KEY)
    orders = sol.OrdersClient(http, CLIENT_ID, CLIENT_SECRET)
    catalog.get_item("SKU-100")
    orders.list_orders()
    with pytest.raises(sol.AuthError) as exc:
        sol.OrdersClient(http, CLIENT_ID, CLIENT_SECRET + "x").list_orders()
    text = " ".join([repr(catalog), str(catalog), repr(orders), str(orders), str(exc.value),
                     capsys.readouterr().out, caplog.text])
    for secret in (API_KEY, CLIENT_SECRET, "tok_00001"):
        assert secret not in text, f"{secret!r} leaked through repr/str, an exception, print or logging"
