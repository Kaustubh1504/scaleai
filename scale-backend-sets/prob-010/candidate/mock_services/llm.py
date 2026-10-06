"""The mock LLM used by the document classifier.

    from mock_services.llm import make_llm
    llm = make_llm()
    resp = llm.complete("Classify this document ... <item>Invoice total amount due</item>", timeout=10)
    resp.text   # '{"label": "invoice", "confidence": 0.91}'

The model only reads the text inside <item>...</item>; instructions can go
anywhere outside the tags. It answers with a JSON object
{"label": <string>, "confidence": <number>} -- usually. Like a real model it can
time out, rate-limit you (LLMRateLimitError.retry_after), fail with a 5xx, wrap
its JSON in a markdown fence, return malformed JSON, invent a label, or give a
different (valid) label when asked the same question twice.

Confidence is deterministic per text: 0.70-0.99 when one label's keywords
clearly win, 0.50-0.69 when two labels tie, 0.30-0.49 when no keyword matches
(the label is then "other").

All errors subclass shared.mock_llm.LLMError and carry ``.retryable``.
See ../../shared/README.md for every knob on LLMConfig.

Run it as an HTTP server instead (optional):
    python -m mock_services.llm_server --port 8001 --failure-rate 0.2
"""

from __future__ import annotations

import mock_services  # noqa: F401  (puts shared/ on sys.path)
from shared.fake_clock import Clock
from shared.mock_llm import KeywordClassifier, LLMConfig, MockLLMClient

LABELS = ("contract", "invoice", "id_document", "support_letter", "other")

KEYWORDS = {
    "contract": ["agreement", "contract", "party", "parties", "clause", "termination", "hereby", "signature"],
    "invoice": ["invoice", "amount due", "total due", "remit", "tax", "billed", "payment terms"],
    "id_document": ["passport", "driver license", "date of birth", "nationality", "identity", "id number"],
    "support_letter": ["complaint", "assistance", "help", "issue", "problem", "sincerely", "dear support"],
}


def make_responder() -> KeywordClassifier:
    return KeywordClassifier(KEYWORDS, default_label="other")


def make_llm(config: LLMConfig | None = None, clock: Clock | None = None) -> MockLLMClient:
    return MockLLMClient(config or LLMConfig(), responder=make_responder(), clock=clock)
