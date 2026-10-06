import random

import pytest

from app.classifier import InvalidOutput, RetryPolicy, TicketClassifier, build_prompt, parse_output
from mock_services.clock import FakeClock
from mock_services.llm import make_llm
from shared.mock_llm import FunctionResponder, LLMConfig, MockLLMClient

TICKET = {"ticket_id": "T-1", "subject": "Refund", "body": "Please refund my invoice."}


@pytest.mark.parametrize("text, expected", [
    ('{"label": "bug", "confidence": 0.5}', ("bug", 0.5)),
    ('```json\n{"label": "bug", "confidence": 1}\n```', ("bug", 1.0)),
    ('```\n{"label": " Billing ", "confidence": 0}\n```', ("billing", 0.0)),
])
def test_parse_output_accepts(text, expected):
    assert parse_output(text) == expected


@pytest.mark.parametrize("text", [
    '{"label": "bug"', "{'label': 'bug', 'confidence': 0.5}", '["bug"]',
    '{"label": "Billing Issue", "confidence": 0.5}', '{"label": 3, "confidence": 0.5}',
    '{"label": "bug", "confidence": 1.5}', '{"label": "bug", "confidence": true}', '{"label": "bug"}',
])
def test_parse_output_rejects(text):
    with pytest.raises(InvalidOutput):
        parse_output(text)


def test_prompt_wraps_ticket_in_item_tags():
    prompt = build_prompt(TICKET)
    assert "<item>Refund\nPlease refund my invoice.</item>" in prompt


def classifier(config: LLMConfig, **policy):
    clock = FakeClock()
    return TicketClassifier(make_llm(config, clock), clock, RetryPolicy(**policy), random.Random(0)), clock


def test_success_first_try():
    c, clock = classifier(LLMConfig())
    assert c.classify(TICKET) == {"ticket_id": "T-1", "status": "classified", "label": "billing",
                                  "confidence": pytest.approx(0.7, abs=0.3), "attempts": 1, "error": None}
    assert clock.sleeps == []


def test_retries_with_backoff_then_succeeds():
    c, clock = classifier(LLMConfig(prompt_faults={"refund": ["server_error", "malformed"]}))
    result = c.classify(TICKET)
    assert result["status"] == "classified" and result["attempts"] == 3
    assert 0.25 <= clock.sleeps[0] <= 0.5 and 0.5 <= clock.sleeps[1] <= 1.0


def test_rate_limit_waits_retry_after():
    c, clock = classifier(LLMConfig(prompt_faults={"refund": ["rate_limit"]}, retry_after_s=3.0))
    assert c.classify(TICKET)["attempts"] == 2
    assert clock.sleeps == [3.0]


def test_gives_up_after_max_attempts_without_final_sleep():
    c, clock = classifier(LLMConfig(prompt_faults={"refund": ["wrong_label"] * 3}))
    result = c.classify(TICKET)
    assert result["status"] == "failed" and result["attempts"] == 3 and "label" in result["error"]
    assert len(clock.sleeps) == 2


def test_non_retryable_error_fails_immediately():
    c, clock = classifier(LLMConfig(max_context_tokens=5))
    result = c.classify(TICKET)
    assert (result["status"], result["attempts"]) == ("failed", 1)
    assert clock.sleeps == []


def test_timeout_is_passed_to_llm():
    c, clock = classifier(LLMConfig(latency_s=30))
    result = c.classify(TICKET)
    assert result["status"] == "failed" and "Timeout" in result["error"]


def test_backoff_is_capped():
    policy = RetryPolicy()
    assert 4.0 <= policy.backoff(10, random.Random(1)) <= 8.0


def test_custom_responder_output_is_normalized():
    clock = FakeClock()
    llm = MockLLMClient(responder=FunctionResponder(lambda ctx: '{"label": "  BUG ", "confidence": 0.9}'), clock=clock)
    assert TicketClassifier(llm, clock).classify(TICKET)["label"] == "bug"
