"""Part 2: ?classify=true adds an OpenAI category per row: retries, validation, fallback, concurrency."""

import json
import logging
import time

import pytest
from conftest import CATS, FAKE_KEY, HERE, upload

EXPECTED = json.loads((HERE / "expected_sample.json").read_text())
ALLOWED = {"data_labeling", "model_evaluation", "content_moderation", "transcription", "other"}


def categories(r):
    return {row["task_id"]: row["category"] for row in r.json()["rows"]}


def test_categories_with_faults(client):
    r = upload(client, classify=True)
    assert r.status_code == 200, r.text
    assert categories(r) == {row["task_id"]: row["category"] for row in EXPECTED["rows"]}


def test_rows_otherwise_unchanged(client):
    r = upload(client, classify=True)
    assert r.json()["rows"] == EXPECTED["rows"]


def test_classification_failures_reported(client):
    errs = upload(client, classify=True).json()["errors"]
    failed = sorted((e["row"], e["id"]) for e in errs if e["error"] == "classification_failed")
    assert failed == [(11, "T010"), (12, "T011"), (14, "T013")]


@pytest.mark.parametrize("classify", [None, False])
def test_no_classify_means_no_calls(client, llm, monkeypatch, classify):
    monkeypatch.delenv("OPENAI_API_KEY")  # the key is only needed when classify=true
    r = upload(client, classify=classify)
    assert r.status_code == 200, r.text
    assert all("category" not in row for row in r.json()["rows"])
    assert llm.count(None) == 0


@pytest.mark.parametrize("marker,calls", [
    ("Transcribe support call 1042", 1),   # plain success
    ("Caption product photos", 2),         # 429 then ok
    ("Grade chatbot answers", 3),          # 500, 502, ok
    ("Benchmark reasoning model", 4),      # 503 forever: 1 try + 3 retries
    ("Transcribe interview tape 3", 2),    # timeout then ok
    ("Moderate forum posts", 2),           # not JSON once, then ok
    ("Audit label quality", 2),            # disallowed category twice -> fallback
    ("Classify ticket 5531", 2),           # injection: "HACKED" twice -> fallback
])
def test_call_counts(client, llm, marker, calls):
    upload(client, classify=True)
    assert llm.count(marker) == calls


def test_one_call_per_valid_row(client, llm):
    upload(client, classify=True)
    assert llm.count(None) == 1 + 1 + 1 + 1 + 2 + 3 + 2 + 2 + 2 + 4 + 2 + 1  # 22


def test_prompt_contains_title_and_description(client, llm):
    upload(client, classify=True)
    texts = [c["text"] for c in llm.calls if c["marker"] == "Evaluate summarizer v2"]
    desc = 'Rate model summaries for faithfulness; flag any "hallucinated" facts.'
    assert texts and (desc in texts[0] or json.dumps(desc)[1:-1] in texts[0])


def test_key_sent_as_bearer(client, llm):
    upload(client, classify=True)
    assert all(c["headers"].get("authorization") == f"Bearer {FAKE_KEY}" for c in llm.calls)


def test_key_never_leaks(client, caplog, capfd):
    caplog.set_level(logging.INFO)
    r = upload(client, classify=True)
    out, err = capfd.readouterr()
    assert FAKE_KEY not in caplog.text + out + err + r.text


def test_missing_key_is_503(client, llm, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    assert upload(client, classify=True).status_code == 503
    assert llm.count(None) == 0


def test_auth_error_is_not_retried(client, llm, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-wrong")
    r = upload(client, classify=True)
    assert r.status_code == 200
    assert set(categories(r).values()) == {"uncategorized"}
    assert llm.count(None) == 12  # one 401 per row, no retries


def test_bounded_parallelism_and_order(client, llm):
    n = 300
    tasks = "task_id,title,description,user_id,priority\n" + "".join(
        f"L{i:04d},LRG-{i:04d} work item,Generated row {i},U01,{i % 3 + 1}\n" for i in range(1, n + 1))
    llm.delay = 0.02
    t0 = time.monotonic()
    r = upload(client, tasks=tasks.encode(), classify=True)
    elapsed = time.monotonic() - t0
    assert r.status_code == 200, r.text
    got = [(row["task_id"], row["category"]) for row in r.json()["rows"]]
    assert got == [(f"L{i:04d}", CATS[i % 5]) for i in range(1, n + 1)]
    assert llm.count(None) == n
    assert llm.peak <= 10, f"{llm.peak} requests in flight at once (max 10)"
    assert llm.peak >= 5, f"only {llm.peak} in flight at once: calls are not running in parallel"
    assert elapsed < 5, f"took {elapsed:.1f}s; sequential would be ~6s"


@pytest.mark.live
def test_live_openai(workdir):
    import importlib

    from fastapi.testclient import TestClient

    with TestClient(importlib.import_module("app.main").app) as c:
        r = upload(c, classify=True)
    assert r.status_code == 200, r.text
    cats = categories(r)
    assert set(cats.values()) <= ALLOWED | {"uncategorized"}
    assert cats["T001"] == "transcription" and cats["T009"] == "transcription"
    assert cats["T002"] == "data_labeling"
    assert cats["T003"] == "model_evaluation"
    assert cats["T004"] == "content_moderation" and cats["T007"] == "content_moderation"
    assert cats["T010"] != "HACKED"
