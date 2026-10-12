import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def make_client(sol, clock):
    def make():
        return TestClient(sol.create_app(clock=clock))
    return make


@pytest.fixture
def client(make_client):
    return make_client()


def create(client, **body):
    body.setdefault("name", "Street signs")
    return client.post("/projects", json=body)


def test_create_returns_201_with_defaults(client):
    """POST /projects returns 201 with id, created_at and defaults (priority 3, tags [])"""
    resp = create(client, name="Street signs")
    assert resp.status_code == 201, resp.text
    assert resp.json() == {
        "id": 1, "name": "Street signs", "priority": 3, "tags": [],
        "created_at": "2023-11-14T22:13:20+00:00",
    }, "created_at should be the clock's time as an ISO 8601 UTC string"
    second = create(client, name="Receipts", priority=5, tags=["ocr", "finance"]).json()
    assert second["id"] == 2 and second["priority"] == 5 and second["tags"] == ["ocr", "finance"]


def test_name_is_stripped_and_validated(client):
    """Names are stripped; blank or over-100-char names are 422"""
    resp = create(client, name="   Lidar   ")
    assert resp.status_code == 201 and resp.json()["name"] == "Lidar", "surrounding whitespace should be stripped"
    assert create(client, name="    ").status_code == 422, "a whitespace-only name is empty after stripping"
    assert create(client, name="x" * 101).status_code == 422
    assert create(client, name="y" * 100).status_code == 201, "exactly 100 chars is allowed"
    assert client.post("/projects", json={"priority": 2}).status_code == 422, "name is required"


def test_priority_and_tags_validated(client):
    """priority outside 1..5 and more than 10 tags are 422"""
    assert create(client, name="a", priority=0).status_code == 422
    assert create(client, name="b", priority=6).status_code == 422
    assert create(client, name="c", tags=[f"t{i}" for i in range(11)]).status_code == 422
    assert create(client, name="d", tags=[f"t{i}" for i in range(10)]).status_code == 201, "10 tags is allowed"


def test_duplicate_name_is_409(client):
    """A duplicate name (case-insensitive, after strip) is 409 with a detail message"""
    assert create(client, name="Street signs").status_code == 201
    resp = create(client, name="  STREET signs ")
    assert resp.status_code == 409, "names must be unique ignoring case"
    assert isinstance(resp.json().get("detail"), str), "error body should be {'detail': '...'}"


def test_get_by_id_and_404(client):
    """GET /projects/{id} returns the project; an unknown id is 404"""
    created = create(client, name="Receipts").json()
    resp = client.get(f"/projects/{created['id']}")
    assert resp.status_code == 200 and resp.json() == created
    missing = client.get("/projects/999")
    assert missing.status_code == 404
    assert "detail" in missing.json()


def test_list_pagination(client):
    """GET /projects pages by limit/offset in id order, total counts everything"""
    for i in range(1, 8):
        create(client, name=f"P{i}")
    body = client.get("/projects", params={"limit": 3, "offset": 2}).json()
    assert [p["name"] for p in body["items"]] == ["P3", "P4", "P5"]
    assert body["total"] == 7, "total is the full count, not the page size"
    default = client.get("/projects").json()
    assert len(default["items"]) == 7 and default["total"] == 7, "default limit is 20"
    past_end = client.get("/projects", params={"offset": 50}).json()
    assert past_end == {"items": [], "total": 7}


def test_list_tag_filter(client):
    """?tag= keeps exact tag matches and total counts the filtered set"""
    create(client, name="A", tags=["vision", "3d"])
    create(client, name="B", tags=["text"])
    create(client, name="C", tags=["vision"])
    create(client, name="D", tags=["visions"])
    body = client.get("/projects", params={"tag": "vision", "limit": 1}).json()
    assert [p["name"] for p in body["items"]] == ["A"]
    assert body["total"] == 2, "total counts filtered projects (A and C), before limit"


def test_list_query_validation(client):
    """limit must be 1..100 and offset >= 0, else 422"""
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "ten"}):
        assert client.get("/projects", params=params).status_code == 422, f"{params} should be rejected"
    assert client.get("/projects", params={"limit": 100}).status_code == 200


def test_patch_updates_only_sent_fields(client):
    """PATCH changes only the fields in the body; id and created_at stay"""
    created = create(client, name="Receipts", priority=2, tags=["ocr"]).json()
    resp = client.patch(f"/projects/{created['id']}", json={"priority": 5})
    assert resp.status_code == 200, resp.text
    assert resp.json() == {**created, "priority": 5}, "fields not in the PATCH body must keep their values"
    resp = client.patch(f"/projects/{created['id']}", json={"name": "  Invoices ", "tags": []})
    assert resp.json() == {**created, "priority": 5, "name": "Invoices", "tags": []}
    assert client.get(f"/projects/{created['id']}").json()["name"] == "Invoices", "the update must be stored"


def test_patch_errors(client):
    """PATCH: unknown id 404, invalid value 422, another project's name 409, own name recased OK"""
    a = create(client, name="Alpha").json()
    create(client, name="Beta")
    assert client.patch("/projects/999", json={"priority": 1}).status_code == 404
    assert client.patch(f"/projects/{a['id']}", json={"priority": 9}).status_code == 422
    assert client.patch(f"/projects/{a['id']}", json={"name": " "}).status_code == 422
    assert client.patch(f"/projects/{a['id']}", json={"name": "BETA"}).status_code == 409
    own = client.patch(f"/projects/{a['id']}", json={"name": "ALPHA"})
    assert own.status_code == 200 and own.json()["name"] == "ALPHA", "renaming to your own name in other case is fine"


def test_delete(client):
    """DELETE returns 204 with no body, then GET and DELETE are 404; ids aren't reused"""
    a = create(client, name="Alpha").json()
    resp = client.delete(f"/projects/{a['id']}")
    assert resp.status_code == 204 and resp.content == b""
    assert client.get(f"/projects/{a['id']}").status_code == 404
    assert client.delete(f"/projects/{a['id']}").status_code == 404
    assert create(client, name="Alpha").json()["id"] == 2, "ids are never reused, and the name is free again"


def test_apps_have_independent_state(make_client):
    """Each create_app() call starts with its own empty store"""
    first, second = make_client(), make_client()
    create(first, name="Alpha")
    assert second.get("/projects").json() == {"items": [], "total": 0}, "state leaked between apps"
    assert create(second, name="Alpha").json()["id"] == 1
