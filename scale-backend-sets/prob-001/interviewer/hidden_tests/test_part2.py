"""Part 2: LLM classification with validation, retries and persistence."""

import json

import pytest

from conftest import EXPECTED_LABELS, make_llm, upload_id_for
from shared.mock_llm import FunctionResponder, LLMConfig, MockLLMClient

LABELS = {"billing", "bug", "account_access", "feature_request", "other"}


def classify(client, upload_id):
    resp = client.post(f"/uploads/{upload_id}/classify")
    assert resp.status_code == 200, resp.text
    return resp.json()


def by_id(body):
    return {r["ticket_id"]: r for r in body["results"]}


def test_happy_path_labels_order_and_shape(make_client):
    client = make_client()
    body = classify(client, upload_id_for(client))
    assert [r["ticket_id"] for r in body["results"]] == list(EXPECTED_LABELS)
    assert {r["ticket_id"]: r["label"] for r in body["results"]} == EXPECTED_LABELS
    assert (body["classified"], body["failed"]) == (9, 0)
    for r in body["results"]:
        assert r["status"] == "classified" and r["attempts"] == 1 and r["error"] is None
        assert 0 <= r["confidence"] <= 1


def test_persisted_and_readable(make_client, tmp_path):
    client = make_client()
    upload_id = upload_id_for(client)
    assert client.get(f"/uploads/{upload_id}/classifications").status_code == 404
    body = classify(client, upload_id)
    assert json.loads((tmp_path / "classifications" / f"{upload_id}.json").read_text()) == body
    got = client.get(f"/uploads/{upload_id}/classifications")
    assert got.status_code == 200 and got.json() == body


def test_unknown_upload_404(make_client):
    client = make_client()
    assert client.post("/uploads/nope/classify").status_code == 404
    assert client.get("/uploads/nope/classifications").status_code == 404


def test_fenced_output_is_accepted(make_client, clock):
    client = make_client(llm=make_llm(LLMConfig(fenced_rate=1.0), clock))
    body = classify(client, upload_id_for(client))
    assert {r["ticket_id"]: r["label"] for r in body["results"]} == EXPECTED_LABELS
    assert all(r["attempts"] == 1 for r in body["results"])


def test_label_case_and_whitespace_normalized(make_client, clock):
    answers = iter(['{"label": " Billing ", "confidence": 0.8}', '```\n{"label": "BUG", "confidence": 1}\n```'])
    llm = MockLLMClient(responder=FunctionResponder(lambda ctx: next(answers, '{"label": "other", "confidence": 0}')),
                        clock=clock)
    client = make_client(llm=llm, max_concurrency=1)
    content = ("ticket_id,customer_email,subject,body,created_at\n"
               "A,a@b.co,s,b,2024-01-01T00:00:00Z\nB,a@b.co,s,b2,2024-01-01T00:00:00Z\n").encode()
    body = classify(client, upload_id_for(client, "t.csv", content))
    assert [(r["label"], r["confidence"]) for r in body["results"]] == [("billing", 0.8), ("bug", 1)]


@pytest.mark.parametrize("fault", ["wrong_label", "malformed", "server_error", "timeout", "rate_limit"])
def test_one_bad_attempt_then_success(make_client, clock, fault):
    llm = make_llm(LLMConfig(prompt_faults={"dark mode": [fault]}, retry_after_s=0.01), clock)
    client = make_client(llm=llm)
    result = by_id(classify(client, upload_id_for(client)))["T-1004"]
    assert (result["status"], result["label"], result["attempts"]) == ("classified", "feature_request", 2)


def test_always_invalid_fails_after_three_attempts(make_client, clock):
    llm = make_llm(LLMConfig(prompt_faults={"dark mode": ["malformed", "wrong_label", "malformed", "ok"]}), clock)
    client = make_client(llm=llm)
    body = classify(client, upload_id_for(client))
    result = by_id(body)["T-1004"]
    assert result["status"] == "failed" and result["attempts"] == 3
    assert result["label"] is None and result["confidence"] is None
    assert isinstance(result["error"], str) and result["error"]
    assert (body["classified"], body["failed"]) == (8, 1)
    dark_mode_calls = [c for c in llm.calls if c.fault in ("malformed", "wrong_label")]
    assert len(dark_mode_calls) == 3


def test_bad_confidence_is_invalid(make_client, clock):
    answers = iter(['{"label": "bug", "confidence": 1.5}', '{"label": "bug", "confidence": true}',
                    '{"label": "bug"}'])
    llm = MockLLMClient(responder=FunctionResponder(lambda ctx: next(answers, '{"label": "bug", "confidence": 0.4}')),
                        clock=clock)
    client = make_client(llm=llm, max_concurrency=1)
    content = "ticket_id,customer_email,subject,body,created_at\nA,a@b.co,s,b,2024-01-01T00:00:00Z\n".encode()
    result = classify(client, upload_id_for(client, "t.csv", content))["results"][0]
    assert result["status"] == "failed" and result["attempts"] == 3


def test_non_retryable_error_fails_immediately(make_client, clock):
    llm = make_llm(LLMConfig(max_context_tokens=40), clock)
    client = make_client(llm=llm)
    long_body = "word " * 200
    content = ("ticket_id,customer_email,subject,body,created_at\n"
               f"LONG,a@b.co,s,{long_body},2024-01-01T00:00:00Z\n").encode()
    result = classify(client, upload_id_for(client, "t.csv", content))["results"][0]
    assert (result["status"], result["attempts"]) == ("failed", 1)
    assert llm.usage.failed_calls == 1


class RecordingLLM:
    """Wraps the mock and records the kwargs of every call."""

    def __init__(self, inner):
        self.inner, self.kwargs, self.prompts = inner, [], []

    def complete(self, prompt, **kwargs):
        self.kwargs.append(kwargs)
        self.prompts.append(prompt)
        return self.inner.complete(prompt, **kwargs)

    async def acomplete(self, prompt, **kwargs):
        self.kwargs.append(kwargs)
        self.prompts.append(prompt)
        return await self.inner.acomplete(prompt, **kwargs)


def test_timeout_and_item_tags(make_client, clock):
    llm = RecordingLLM(make_llm(clock=clock))
    client = make_client(llm=llm)
    classify(client, upload_id_for(client))
    assert llm.kwargs and all(k.get("timeout") == 10 for k in llm.kwargs)
    assert any("<item>" in p and "dark mode feature" in p.split("<item>", 1)[1] for p in llm.prompts)


def test_slow_model_times_out(make_client, clock):
    llm = make_llm(LLMConfig(latency_s=15), clock)
    client = make_client(llm=llm)
    content = "ticket_id,customer_email,subject,body,created_at\nA,a@b.co,s,b,2024-01-01T00:00:00Z\n".encode()
    result = classify(client, upload_id_for(client, "t.csv", content))["results"][0]
    assert (result["status"], result["attempts"]) == ("failed", 3)


def test_llm_errors_never_escape(make_client, clock):
    llm = make_llm(LLMConfig(failure_rate=0.5, malformed_rate=0.3, seed=5), clock)
    client = make_client(llm=llm)
    body = classify(client, upload_id_for(client))
    assert body["classified"] + body["failed"] == 9
    assert all(r["label"] in LABELS for r in body["results"] if r["status"] == "classified")
    assert all(1 <= r["attempts"] <= 3 for r in body["results"])
