"""Part 1: input validation, one LLM call, lenient parsing, strict output validation."""

import json

import pytest
from conftest import GOOD, ticket, triage

KEYS = {"category", "urgency", "summary"}


@pytest.mark.parametrize("marker", ["[ticket-01]", "[ticket-02]", "[ticket-03]", "[ticket-04]"])
def test_clean_and_fenced_json(client, llm, marker):
    r = triage(client, ticket(marker))
    assert r.status_code == 200, r.text
    assert r.json() == GOOD
    assert llm.count(marker) == 1


def test_extra_keys_ignored(client, llm):
    r = triage(client, ticket("[ticket-05]"))
    assert r.status_code == 200, r.text
    assert set(r.json()) == KEYS
    assert r.json() == GOOD
    assert "RAW-MODEL-NOTE" not in r.text


def test_response_has_exactly_three_keys(client):
    body = triage(client, ticket("[ticket-09]")).json()
    assert set(body) == KEYS
    assert body == {"category": "feature_request", "urgency": 5, "summary": "Wants dark mode."}
    assert type(body["urgency"]) is int


def test_summary_is_stripped(client):
    r = triage(client, ticket("[ticket-07]"))
    assert r.status_code == 200, r.text
    assert r.json()["summary"] == "Export button crashes the app."


def test_summary_200_chars_is_ok(client):
    r = triage(client, ticket("[ticket-08]"))
    assert r.status_code == 200, r.text
    assert r.json() == {"category": "billing", "urgency": 1, "summary": "x" * 200}


def test_string_urgency_rejected_then_valid(client, llm):
    r = triage(client, ticket("[ticket-06]"))
    assert r.status_code == 200, r.text
    assert r.json() == GOOD
    assert llm.count("[ticket-06]") == 2


@pytest.mark.parametrize("marker", [
    "[ticket-20]",  # urgency 9
    "[ticket-21]",  # urgency 0
    "[ticket-22]",  # urgency true
    "[ticket-23]",  # urgency "3"
    "[ticket-24]",  # urgency 3.0
    "[ticket-25]",  # category HACKED
    "[ticket-26]",  # category "Billing" (case)
    "[ticket-27]",  # 250-char summary
    "[ticket-28]",  # whitespace-only summary
    "[ticket-29]",  # summary not a string
    "[ticket-30]",  # missing field
    "[ticket-31]",  # JSON array, not an object
])
def test_invalid_schema_rejected(client, llm, marker):
    r = triage(client, ticket(marker))
    assert r.status_code == 502, r.text
    assert r.json() == {"detail": "llm_bad_response"}


@pytest.mark.parametrize("text", [
    "",
    "   ",
    " \n\t ",
    "a" * 5001,
    " " * 5001,
])
def test_bad_text_is_422(client, llm, text):
    assert triage(client, text).status_code == 422
    assert llm.count(None) == 0


@pytest.mark.parametrize("body", [{}, {"text": None}, {"text": 123}, {"text": ["hi"]}, {"txt": "hi"}])
def test_bad_body_is_422(client, llm, body):
    assert client.post("/triage", json=body).status_code == 422
    assert llm.count(None) == 0


def test_exactly_5000_chars_ok(client, llm):
    r = triage(client, "b" * 5000)
    assert r.status_code == 200, r.text
    assert llm.count(None) == 1


def test_one_call_on_success(client, llm):
    triage(client, ticket("[ticket-01]"))
    assert llm.count(None) == 1


def test_ticket_text_in_prompt(client, llm):
    text = ticket("[ticket-01]", 'Export to "CSV" fails with error E-7731 since Tuesday.')
    triage(client, text)
    sent = llm.calls[0]["text"]
    assert text in sent or json.dumps(text)[1:-1] in sent


def test_prompt_asks_for_json_and_names_categories(client, llm):
    triage(client, ticket("[ticket-01]"))
    sent = llm.calls[0]["text"]
    assert "json" in sent.lower()
    for c in ("bug", "billing", "account", "feature_request", "other"):
        assert c in sent


@pytest.mark.live
def test_live_openai():
    import importlib

    from fastapi.testclient import TestClient

    text = ("Hi, I was charged twice for my Pro subscription this month (two $49 charges on my card "
            "on the 3rd). Please refund the duplicate charge and send me a corrected invoice.")
    with TestClient(importlib.import_module("app.main").app) as c:
        r = triage(c, text)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == KEYS
    assert body["category"] == "billing"
    assert type(body["urgency"]) is int and 1 <= body["urgency"] <= 5
    assert isinstance(body["summary"], str) and 1 <= len(body["summary"]) <= 200
