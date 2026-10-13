from fastapi.testclient import TestClient

from app.main import create_app
from mock_services.clock import FakeClock
from mock_services.llm import make_llm
from shared.mock_llm import LLMConfig


def make_client(tmp_path, config=None):
    clock = FakeClock()
    llm = make_llm(config or LLMConfig(seed=1), clock=clock)
    return TestClient(create_app(storage_dir=tmp_path, llm=llm, clock=clock)), clock


def upload_sample(client):
    with open("data/tickets.csv", "rb") as f:
        return client.post("/uploads", files={"file": ("tickets.csv", f)})


# ---- Part 1 ----

def test_upload_sample_file(tmp_path):
    client, _ = make_client(tmp_path)
    r = upload_sample(client)
    assert r.status_code == 201
    body = r.json()
    assert body["total_rows"] == 18
    assert body["valid_rows"] == 9
    assert body["errors"][0] == {"row": 6, "field": "customer_email", "message": "invalid email"}

    saved = client.get("/uploads/" + body["upload_id"]).json()
    assert len(saved["tickets"]) == 9


def test_wrong_extension_and_unknown_id(tmp_path):
    client, _ = make_client(tmp_path)
    r = client.post("/uploads", files={"file": ("t.txt", b"hello")})
    assert r.status_code == 415
    assert client.get("/uploads/doesnotexist").status_code == 404


# ---- Part 2 ----

def test_classify_happy_path(tmp_path):
    client, _ = make_client(tmp_path)
    upload_id = upload_sample(client).json()["upload_id"]
    body = client.post("/uploads/" + upload_id + "/classify").json()
    assert body["classified"] == 9
    assert body["results"][0]["label"] == "billing"   # T-1001, "charged twice"


def test_retries_then_gives_up(tmp_path):
    client, _ = make_client(tmp_path, LLMConfig(seed=1, prompt_faults={
        "T-1001": ["timeout", "malformed"],                 # fails twice, then works
        "T-1002": ["server_error", "wrong_label", "timeout"],  # fails all 3
    }))
    upload_id = upload_sample(client).json()["upload_id"]
    results = client.post("/uploads/" + upload_id + "/classify").json()["results"]
    assert results[0]["status"] == "classified" and results[0]["attempts"] == 3
    assert results[1]["status"] == "failed" and results[1]["attempts"] == 3


# ---- Part 3 ----

def test_backoff_waits(tmp_path):
    client, clock = make_client(tmp_path, LLMConfig(seed=1, prompt_faults={
        "T-1001": ["server_error", "server_error"]}))
    upload_id = upload_sample(client).json()["upload_id"]
    client.post("/uploads/" + upload_id + "/classify")
    assert len(clock.sleeps) == 2
    assert 0.25 <= clock.sleeps[0] <= 0.5   # after attempt 1
    assert 0.5 <= clock.sleeps[1] <= 1.0    # after attempt 2


def test_rerun_keeps_results(tmp_path):
    client, _ = make_client(tmp_path)
    upload_id = upload_sample(client).json()["upload_id"]
    first = client.post("/uploads/" + upload_id + "/classify").json()
    second = client.post("/uploads/" + upload_id + "/classify").json()
    assert first == second
