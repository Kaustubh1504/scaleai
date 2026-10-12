import pytest

from problem_api import make_api

EXPECTED = [
    {"id": "w_001", "name": "Diego Alvarez", "role": "annotator"},
    {"id": "w_002", "name": "Ana Silva", "role": "reviewer"},
    {"id": "w_003", "name": "Fatima Zahra", "role": "lead"},
    {"id": "w_004", "name": "Priya Raman", "role": "annotator"},
    {"id": "w_005", "name": "Jonas Berg", "role": "lead"},
    {"id": "w_006", "name": "Sam Okafor", "role": "reviewer"},
    {"id": "w_007", "name": "Mei Lin", "role": "annotator"},
]


def test_unwrap_list_and_data(sol):
    """A bare list and {"data": [...]} both unwrap to the list"""
    recs = [{"id": 1}, {"id": 2}]
    assert sol.unwrap(recs) == recs
    assert sol.unwrap({"data": recs, "meta": {"count": 2}}) == recs
    assert sol.unwrap([]) == []


def test_unwrap_nested_items(sol):
    """{"results": {"items": [...]}} and {"data": {"items": [...]}} unwrap to the inner list"""
    recs = [{"id": "a"}]
    assert sol.unwrap({"results": {"items": recs, "count": 1}}) == recs
    assert sol.unwrap({"data": {"items": recs, "next": None}}) == recs
    assert sol.unwrap({"data": {"results": recs}}) == recs, "an inner 'results' list counts too"


def test_unwrap_single_object(sol):
    """{"data": {...a record...}} becomes a one-element list"""
    rec = {"id": 9, "name": "solo"}
    assert sol.unwrap({"data": rec}) == [rec]
    assert sol.unwrap({"data": {"id": 1, "items": "not-a-list"}}) == [{"id": 1, "items": "not-a-list"}], \
        "an 'items' key that isn't a list doesn't make it an envelope"


def test_unwrap_empty_variants(sol):
    """{"items": []} and {"data": null} both give []"""
    assert sol.unwrap({"items": []}) == []
    assert sol.unwrap({"data": None}) == []
    assert sol.unwrap({"results": {"items": []}}) == []


def test_unwrap_key_precedence(sol):
    """When several envelope keys are present, 'data' beats 'results' beats 'items'"""
    assert sol.unwrap({"items": [{"id": "i"}], "data": [{"id": "d"}]}) == [{"id": "d"}]
    assert sol.unwrap({"items": [{"id": "i"}], "results": [{"id": "r"}]}) == [{"id": "r"}]


def test_unwrap_unknown_shape(sol):
    """An unknown envelope raises UnexpectedShape carrying the sorted top-level keys"""
    with pytest.raises(sol.UnexpectedShape) as exc:
        sol.unwrap({"payload": [], "ok": True})
    assert exc.value.keys == ["ok", "payload"]
    with pytest.raises(sol.UnexpectedShape) as exc:
        sol.unwrap({"data": "oops", "z": 1})
    assert exc.value.keys == ["data", "z"], "a string under 'data' is not a known shape"


def test_unwrap_non_container(sol):
    """A body that's neither list nor dict (string, number, None) raises UnexpectedShape([])"""
    for body in ("hello", 42, None):
        with pytest.raises(sol.UnexpectedShape) as exc:
            sol.unwrap(body)
        assert exc.value.keys == [], f"unwrap({body!r}) should report no keys"


def test_fetch_everything_normalized_and_sorted(sol):
    """fetch_everything merges all three endpoints into {id, name, role}, sorted by id"""
    api = make_api()
    assert sol.fetch_everything(api.client()) == EXPECTED


def test_fetch_each_endpoint_once(sol):
    """Exactly one GET per endpoint"""
    api = make_api()
    sol.fetch_everything(api.client())
    for path in ("/v1/annotators", "/v1/reviewers", "/v1/leads"):
        assert len(api.calls("GET", path)) == 1, f"expected exactly one request to {path}"
    assert len(api.log) == 3


def test_fetch_with_alternate_lead_envelopes(sol):
    """Leads as a single object or as {"items": []} still work"""
    single = sol.fetch_everything(make_api(leads_shape="single").client())
    assert [p["id"] for p in single if p["role"] == "lead"] == ["w_005"]
    empty = sol.fetch_everything(make_api(leads_shape="empty").client())
    assert [p for p in empty if p["role"] == "lead"] == []
    assert len(empty) == 5


def test_fetch_errors(sol):
    """Unknown envelope propagates UnexpectedShape; a 500 raises ApiError(500, path)"""
    with pytest.raises(sol.UnexpectedShape):
        sol.fetch_everything(make_api(reviewers_shape="bad").client())
    api = make_api()
    api.script("GET /v1/leads", [500])
    with pytest.raises(sol.ApiError) as exc:
        sol.fetch_everything(api.client())
    assert exc.value.status == 500
    assert exc.value.path == "/v1/leads"
