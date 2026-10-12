import warnings

import pytest

warnings.filterwarnings("ignore", message="Using `httpx`")  # starlette TestClient notice
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def make(sol):
    """make(dir) -> a TestClient over a fresh create_app(dir): calling it again is a 'restart'."""
    return lambda d: TestClient(sol.create_app(d))


def task(id, title, assignee=None, status="open"):
    return {"id": id, "title": title, "assignee": assignee, "status": status}


def expect(resp, status):
    assert resp.status_code == status, f"expected {status}, got {resp.status_code}: {resp.text[:300]}"
    return resp.json()


def listed(client):
    return expect(client.get("/tasks"), 200)["tasks"]


def test_create_and_get(make, tmp_path):
    """POST creates (201, status open, assignee null by default); GET returns it; unknown id is 404"""
    c = make(tmp_path)
    assert expect(c.post("/tasks", json={"id": "t1", "title": "Review batch 7"}), 201) == task("t1", "Review batch 7")
    assert expect(c.post("/tasks", json={"id": "t2", "title": "QA", "assignee": "ana"}), 201) == \
        task("t2", "QA", "ana")
    assert expect(c.get("/tasks/t1"), 200) == task("t1", "Review batch 7")
    expect(c.get("/tasks/nope"), 404)


def test_validation_is_422(make, tmp_path):
    """Bad ids, empty titles and unknown statuses are 422 and create nothing"""
    c = make(tmp_path)
    for body in ({"id": "has space", "title": "x"}, {"id": "../etc", "title": "x"}, {"id": "", "title": "x"},
                 {"id": "a" * 65, "title": "x"}, {"id": "ok", "title": ""}, {"title": "no id"}):
        assert c.post("/tasks", json=body).status_code == 422, f"{body} should be rejected with 422"
    expect(c.post("/tasks", json={"id": "ok", "title": "x"}), 201)
    assert c.put("/tasks/ok", json={"title": "x", "status": "closed"}).status_code == 422
    assert [t["id"] for t in listed(c)] == ["ok"]


def test_list_in_creation_order(make, tmp_path):
    """GET /tasks lists in creation order; updating a task does not move it"""
    c = make(tmp_path)
    for tid in ("zeta", "alpha", "mid"):
        expect(c.post("/tasks", json={"id": tid, "title": tid.upper()}), 201)
    expect(c.put("/tasks/zeta", json={"title": "Z2"}), 200)
    assert [t["id"] for t in listed(c)] == ["zeta", "alpha", "mid"], "order must be creation order, not id order"


def test_put_is_full_replace(make, tmp_path):
    """PUT replaces title/assignee/status (missing assignee -> null, missing status -> open); unknown id is 404"""
    c = make(tmp_path)
    expect(c.post("/tasks", json={"id": "t1", "title": "A", "assignee": "ana"}), 201)
    assert expect(c.put("/tasks/t1", json={"title": "B", "assignee": "ben", "status": "done"}), 200) == \
        task("t1", "B", "ben", "done")
    assert expect(c.put("/tasks/t1", json={"title": "C"}), 200) == task("t1", "C"), \
        "a missing assignee means null and a missing status means open"
    assert expect(c.get("/tasks/t1"), 200) == task("t1", "C")
    expect(c.put("/tasks/ghost", json={"title": "x"}), 404)
    assert [t["id"] for t in listed(c)] == ["t1"], "PUT on an unknown id must not create it"


def test_retry_is_idempotent(make, tmp_path):
    """Re-POSTing an existing id with the same title/assignee is 200 with the stored task, no duplicate"""
    c = make(tmp_path)
    expect(c.post("/tasks", json={"id": "t1", "title": "A"}), 201)
    assert expect(c.post("/tasks", json={"id": "t1", "title": "A"}), 200) == task("t1", "A")
    assert expect(c.post("/tasks", json={"id": "t1", "title": "A", "assignee": None}), 200) == task("t1", "A"), \
        "an explicit null assignee equals a missing one"
    expect(c.put("/tasks/t1", json={"title": "A", "status": "done"}), 200)
    assert expect(c.post("/tasks", json={"id": "t1", "title": "A"}), 200) == task("t1", "A", status="done"), \
        "a retry returns the stored task as it is now, unchanged"
    assert len(listed(c)) == 1


def test_conflicting_create_is_409(make, tmp_path):
    """Re-POSTing an existing id with a different title or assignee is 409 and changes nothing"""
    c = make(tmp_path)
    expect(c.post("/tasks", json={"id": "t1", "title": "A", "assignee": "ana"}), 201)
    for body in ({"id": "t1", "title": "B", "assignee": "ana"}, {"id": "t1", "title": "A"},
                 {"id": "t1", "title": "A", "assignee": "ben"}):
        assert c.post("/tasks", json=body).status_code == 409, f"{body} conflicts with the stored task"
    assert expect(c.get("/tasks/t1"), 200) == task("t1", "A", "ana")


def test_restart_sees_everything(make, tmp_path):
    """A new app over the same storage_dir sees every create and update, in order"""
    c = make(tmp_path)
    expect(c.post("/tasks", json={"id": "b", "title": "B"}), 201)
    expect(c.post("/tasks", json={"id": "a", "title": "A", "assignee": "ana"}), 201)
    expect(c.put("/tasks/b", json={"title": "B2", "status": "done"}), 200)

    after = make(tmp_path)
    assert listed(after) == [task("b", "B2", status="done"), task("a", "A", "ana")]
    assert expect(after.get("/tasks/a"), 200) == task("a", "A", "ana")


def test_every_write_is_durable_immediately(make, tmp_path):
    """After each single write, a restart sees exactly the state so far (no batching, no shutdown hook)"""
    c = make(tmp_path)
    expected = []
    for i in range(6):
        tid = f"t{i}"
        expect(c.post("/tasks", json={"id": tid, "title": f"T{i}"}), 201)
        expected.append(task(tid, f"T{i}"))
        assert listed(make(tmp_path)) == expected, f"restart after creating {tid} lost data"
        expect(c.put(f"/tasks/{tid}", json={"title": f"T{i}!", "status": "done"}), 200)
        expected[-1] = task(tid, f"T{i}!", status="done")
        assert listed(make(tmp_path)) == expected, f"restart after updating {tid} lost data"


def test_retry_after_restart(make, tmp_path):
    """Idempotency survives a restart: same body is 200, different body is 409"""
    expect(make(tmp_path).post("/tasks", json={"id": "t1", "title": "A"}), 201)
    c = make(tmp_path)
    assert expect(c.post("/tasks", json={"id": "t1", "title": "A"}), 200) == task("t1", "A")
    assert c.post("/tasks", json={"id": "t1", "title": "Z"}).status_code == 409
    assert len(listed(c)) == 1


def test_storage_dirs_are_isolated_and_created(make, tmp_path):
    """Different storage_dirs don't share data; a missing nested storage_dir is created"""
    one, two = make(tmp_path / "one" / "nested"), make(tmp_path / "two")
    expect(one.post("/tasks", json={"id": "t1", "title": "A"}), 201)
    assert listed(two) == [], "a different storage_dir must start empty"
    expect(two.post("/tasks", json={"id": "t1", "title": "Different"}), 201)
    assert expect(make(tmp_path / "one" / "nested").get("/tasks/t1"), 200)["title"] == "A"


def test_no_temp_files_left_behind(make, tmp_path):
    """After many writes the storage dir holds no leftover *.tmp files"""
    c = make(tmp_path)
    for i in range(25):
        expect(c.post("/tasks", json={"id": f"t{i}", "title": "x"}), 201)
        expect(c.put(f"/tasks/t{i}", json={"title": "y"}), 200)
    leftovers = [p.name for p in tmp_path.rglob("*.tmp")]
    assert leftovers == [], f"temporary files left behind: {leftovers}"
    assert any(tmp_path.rglob("*")), "nothing was written under storage_dir"
