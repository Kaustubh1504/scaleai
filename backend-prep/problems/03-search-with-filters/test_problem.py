from datetime import datetime, timedelta, timezone

import httpx
import pytest

from problem_api import ORDERS, make_api, search

UTC = timezone.utc
IST = timezone(timedelta(hours=5, minutes=30))
PST = timezone(timedelta(hours=-8))


def ids(orders):
    return [o["id"] for o in orders]


def sent(api):
    assert len(api.log) == 1, f"expected exactly one request, saw {len(api.log)}"
    return api.log[0].multi_params


def test_no_filters_sends_no_params(sol):
    """With no arguments, sends GET /v1/orders with no query params and returns data"""
    api = make_api()
    got = sol.search_orders(api.client())
    assert sent(api) == [], f"no params should be sent, got {sent(api)}"
    assert api.log[0].method == "GET" and api.log[0].path == "/v1/orders"
    assert ids(got) == ids(search(ORDERS)), "return the server's `data` list unchanged"


def test_status_is_repeated(sol):
    """status=["paid", "shipped"] is sent as two status= params, in order"""
    api = make_api()
    got = sol.search_orders(api.client(), status=["paid", "shipped"])
    assert [v for k, v in sent(api) if k == "status"] == ["paid", "shipped"], \
        f"send one status= per value (status=paid&status=shipped), got {sent(api)}"
    assert ids(got) == ids(search(ORDERS, statuses=["paid", "shipped"]))


def test_empty_status_list_sends_nothing(sol):
    """status=[] sends no status param"""
    api = make_api()
    sol.search_orders(api.client(), status=[])
    assert sent(api) == []


def test_datetimes_converted_to_utc_z(sol):
    """since/until in other timezones are sent as UTC 'YYYY-MM-DDTHH:MM:SSZ'"""
    api = make_api()
    since = datetime(2024, 3, 4, 0, 0, 0, 123456, tzinfo=IST)
    until = datetime(2024, 3, 5, 4, 0, tzinfo=PST)
    got = sol.search_orders(api.client(), since=since, until=until)
    params = dict(sent(api))
    assert params.get("since") == "2024-03-03T18:30:00Z", f"since: got {params.get('since')!r}"
    assert params.get("until") == "2024-03-05T12:00:00Z", f"until: got {params.get('until')!r}"
    assert ids(got) == ids(search(ORDERS, since=since, until=until))


def test_naive_datetime_rejected(sol):
    """A naive since or until raises ValueError before any request"""
    api = make_api()
    with pytest.raises(ValueError):
        sol.search_orders(api.client(), since=datetime(2024, 3, 4))
    with pytest.raises(ValueError):
        sol.search_orders(api.client(), since=datetime(2024, 3, 1, tzinfo=UTC), until=datetime(2024, 3, 4))
    assert api.log == [], "validate before sending anything"


def test_falsy_values_are_still_sent(sol):
    """min_total_cents=0 and include_archived=False are sent (0 and False are not None)"""
    api = make_api()
    sol.search_orders(api.client(), min_total_cents=0, include_archived=False)
    params = dict(sent(api))
    assert params.get("min_total_cents") == "0", "min_total_cents=0 was given, so send it"
    assert params.get("include_archived") == "false", "booleans go as lower-case 'true'/'false'"


def test_include_archived_true(sol):
    """include_archived=True is sent as 'true' and archived orders come back"""
    api = make_api()
    got = sol.search_orders(api.client(), include_archived=True, min_total_cents=20000)
    params = dict(sent(api))
    assert params.get("include_archived") == "true"
    assert params.get("min_total_cents") == "20000"
    assert ids(got) == ids(search(ORDERS, include_archived=True, min_total=20000))
    assert "ord_006" in ids(got)


def test_full_example(sol):
    """The statement's example sends exactly the 5 expected params and returns ord_008, ord_012, ord_009"""
    api = make_api()
    got = sol.search_orders(api.client(), status=["paid", "shipped"], since=datetime(2024, 3, 4, tzinfo=IST),
                            include_archived=False, sort="-total_cents")
    assert sorted(sent(api)) == sorted([("status", "paid"), ("status", "shipped"), ("since", "2024-03-03T18:30:00Z"),
                                        ("include_archived", "false"), ("sort", "-total_cents")])
    assert ids(got) == ["ord_008", "ord_012", "ord_009"]


def test_bad_sort_and_negative_min_rejected(sol):
    """An unknown sort or a negative min_total_cents raises ValueError before any request"""
    api = make_api()
    for kwargs in ({"sort": "price"}, {"sort": "created_at desc"}, {"min_total_cents": -1}):
        with pytest.raises(ValueError):
            sol.search_orders(api.client(), **kwargs)
            pytest.fail(f"search_orders(**{kwargs}) should raise ValueError")
    assert api.log == []


def test_server_error_raises_http_status_error(sol):
    """A 500 from the server raises httpx.HTTPStatusError"""
    api = make_api()
    api.script("GET /v1/orders", [500])
    with pytest.raises(httpx.HTTPStatusError):
        sol.search_orders(api.client(), sort="created_at")
