import json

import pytest

from app.classifier import Classification, DocumentClassifier
from app.routing import Route, route
from mock_services.clock import FakeClock
from mock_services.llm import make_llm
from shared.mock_llm import FunctionResponder, LLMConfig, MockLLMClient

DOC = {"doc_id": "X-1", "title": "a.pdf", "text": "Invoice: amount due $10, tax included."}


@pytest.mark.parametrize("result, threshold, expected", [
    (Classification("invoice", 0.8, 1), 0.8, Route("auto_accepted", "invoice", None)),
    (Classification("invoice", 0.79, 1), 0.8, Route("needs_review", None, "low_confidence")),
    (Classification("invoice", 0.0, 1), 0.0, Route("auto_accepted", "invoice", None)),
    (Classification(None, None, 3, "invalid output"), 0.0, Route("needs_review", None, "classification_failed")),
    (Classification("invoice", 0.99, 2, agreed=False), 0.5, Route("needs_review", None, "disagreement")),
])
def test_route(result, threshold, expected):
    assert route(result, threshold) == expected


def scripted(answers):
    it = iter(answers)
    return MockLLMClient(responder=FunctionResponder(lambda ctx: next(it)), clock=FakeClock())


def test_one_sample_by_default():
    llm = make_llm(LLMConfig(seed=1), clock=FakeClock())
    result = DocumentClassifier(llm).classify(DOC)
    assert (result.label, result.attempts, result.agreed) == ("invoice", 1, True)
    assert llm.usage.calls == 1


def test_two_samples_take_the_lower_confidence():
    llm = scripted(['{"label": "invoice", "confidence": 0.9}', '{"label": "invoice", "confidence": 0.6}'])
    result = DocumentClassifier(llm).classify(DOC, samples=2)
    assert (result.label, result.confidence, result.attempts, result.agreed) == ("invoice", 0.6, 2, True)


def test_two_samples_disagree():
    llm = scripted(['{"label": "invoice", "confidence": 0.9}', '{"label": "contract", "confidence": 0.9}'])
    result = DocumentClassifier(llm).classify(DOC, samples=2)
    assert (result.label, result.agreed) == ("invoice", False)


def test_failed_first_sample_stops():
    llm = scripted(["nope"] * 3 + [json.dumps({"label": "invoice", "confidence": 0.9})])
    result = DocumentClassifier(llm).classify(DOC, samples=2)
    assert (result.ok, result.attempts) == (False, 3)


def test_failed_second_sample_fails_with_total_attempts():
    llm = scripted(['```json\n{"label": "invoice", "confidence": 0.9}\n```', "x", "y", "z"])
    result = DocumentClassifier(llm).classify(DOC, samples=2)
    assert (result.ok, result.label, result.confidence, result.attempts) == (False, None, None, 4)
    assert "invalid output" in result.error
