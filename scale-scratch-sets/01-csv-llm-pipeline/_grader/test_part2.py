"""Part 2: per-row OpenAI classification with retries, validation and fallback."""

import json
import logging
from pathlib import Path

import pytest
from conftest import FAKE_KEY, HERE, convert

EXPECTED = json.loads((HERE / "expected_sample.json").read_text())
ALLOWED = {"data_labeling", "model_evaluation", "content_moderation", "transcription", "other"}


def categories():
    return {r["task_id"]: r["category"] for r in json.loads(Path("output/tasks.json").read_text())}


def test_categories_with_faults(client):
    r = convert(client)
    assert r.status_code == 200, r.text
    assert categories() == {r["task_id"]: r["category"] for r in EXPECTED["rows"]}


def test_classification_failures_reported(client):
    errs = convert(client).json()["errors"]
    failed = sorted((e["row"], e["id"]) for e in errs if e["error"] == "classification_failed")
    assert failed == [(11, "T010"), (12, "T011"), (14, "T013")]


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
    convert(client)
    assert llm.count(marker) == calls


def test_one_call_per_valid_row(client, llm):
    convert(client)
    assert llm.count(None) == 1 + 1 + 1 + 1 + 2 + 3 + 2 + 2 + 2 + 4 + 2 + 1  # 22


def test_prompt_contains_title_and_description(client, llm):
    convert(client)
    texts = [c["text"] for c in llm.calls if c["marker"] == "Evaluate summarizer v2"]
    desc = 'Rate model summaries for faithfulness; flag any "hallucinated" facts.'
    assert texts and (desc in texts[0] or json.dumps(desc)[1:-1] in texts[0])


def test_key_sent_as_bearer(client, llm):
    convert(client)
    assert all(c["headers"].get("authorization") == f"Bearer {FAKE_KEY}" for c in llm.calls)


def test_key_never_leaks(client, caplog, capfd):
    caplog.set_level(logging.INFO)
    r = convert(client)
    out, err = capfd.readouterr()
    assert FAKE_KEY not in caplog.text + out + err + r.text
    assert FAKE_KEY not in Path("output/tasks.json").read_text()


def test_missing_key_is_503(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    assert convert(client).status_code == 503


def test_auth_error_is_not_retried(client, llm, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-wrong")
    r = convert(client)
    assert r.status_code == 200
    assert set(categories().values()) == {"uncategorized"}
    assert llm.count(None) == 12  # one 401 per row, no retries


@pytest.mark.live
def test_live_openai(workdir):
    import importlib

    from fastapi.testclient import TestClient

    with TestClient(importlib.import_module("app.main").app) as c:
        r = convert(c)
    assert r.status_code == 200, r.text
    cats = categories()
    assert set(cats.values()) <= ALLOWED | {"uncategorized"}
    assert cats["T001"] == "transcription" and cats["T009"] == "transcription"
    assert cats["T002"] == "data_labeling"
    assert cats["T003"] == "model_evaluation"
    assert cats["T004"] == "content_moderation" and cats["T007"] == "content_moderation"
    assert cats["T010"] != "HACKED"
