"""The mock LLM used by this service.

    from mock_services.llm import make_llm
    llm = make_llm()
    resp = llm.complete("Classify this ticket ... <item>I was charged twice</item>", timeout=10)
    resp.text   # '{"label": "billing", "confidence": 0.91}'

The model only reads the text inside <item>...</item>; your instructions can go
anywhere outside the tags. It answers with a JSON object
{"label": <string>, "confidence": <number>} -- usually. Like a real model it can
time out, rate-limit you (LLMRateLimitError.retry_after), fail with a 5xx, wrap
its JSON in a markdown fence, return malformed JSON, or invent a label.

All errors subclass shared.mock_llm.LLMError and carry ``.retryable``.
See ../../shared/README.md for every knob on LLMConfig.

Run it as an HTTP server instead (optional):
    python -m mock_services.llm_server --port 8001 --failure-rate 0.2
"""

from __future__ import annotations

import mock_services  # noqa: F401  (puts shared/ on sys.path)
from shared.fake_clock import Clock
from shared.mock_llm import KeywordClassifier, LLMConfig, MockLLMClient

LABELS = ("billing", "bug", "account_access", "feature_request", "other")

KEYWORDS = {
    "billing": ["invoice", "charge", "charged", "refund", "payment", "billing", "subscription", "price"],
    "bug": ["error", "crash", "broken", "bug", "fail", "exception", "freeze"],
    "account_access": ["password", "login", "locked", "2fa", "sign in", "reset"],
    "feature_request": ["feature", "wish", "would love", "suggestion", "roadmap"],
}


def make_responder() -> KeywordClassifier:
    return KeywordClassifier(KEYWORDS, default_label="other")


def make_llm(config: LLMConfig | None = None, clock: Clock | None = None) -> MockLLMClient:
    return MockLLMClient(config or LLMConfig(), responder=make_responder(), clock=clock)
