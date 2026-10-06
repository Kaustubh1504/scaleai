"""Classify one document with the LLM: build the prompt, parse and validate the answer, retry."""

from __future__ import annotations

import json
from dataclasses import dataclass

from mock_services.llm import LABELS
from shared.mock_llm import LLMError

PROMPT = """You are a document intake assistant. Classify the customer document into exactly one label.
Allowed labels: {labels}.
Respond with only a JSON object: {{"label": "<label>", "confidence": <number between 0 and 1>}}.

<item>{title}

{text}</item>"""


class InvalidOutput(ValueError):
    """The model answered, but not with a usable classification."""


@dataclass(frozen=True)
class Classification:
    """Outcome of classifying one document. ``error`` is set exactly when it failed."""

    label: str | None
    confidence: float | None
    attempts: int
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def build_prompt(doc: dict) -> str:
    return PROMPT.format(labels=", ".join(LABELS), title=doc["title"], text=doc["text"])


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        text = text[first_newline + 1 :] if first_newline != -1 else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def parse_output(text: str) -> tuple[str, float]:
    """Return (label, confidence) or raise InvalidOutput."""
    try:
        data = json.loads(_strip_fence(text))
    except json.JSONDecodeError as exc:
        raise InvalidOutput(f"output is not JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise InvalidOutput("output is not a JSON object")
    label, confidence = data.get("label"), data.get("confidence")
    if not isinstance(label, str) or label.strip().lower() not in LABELS:
        raise InvalidOutput(f"label {label!r} is not one of {', '.join(LABELS)}")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise InvalidOutput(f"confidence {confidence!r} is not a number in [0, 1]")
    return label.strip().lower(), float(confidence)


class DocumentClassifier:
    """Calls the model up to ``max_attempts`` times per document.

    Retryable LLM errors and invalid outputs are retried; a non-retryable error
    fails the document immediately. No backoff yet: the provider has not
    rate-limited us so far.
    """

    def __init__(self, llm, max_attempts: int = 3, timeout_s: float = 10.0):
        self.llm = llm
        self.max_attempts = max_attempts
        self.timeout_s = timeout_s

    def classify(self, doc: dict) -> Classification:
        prompt = build_prompt(doc)
        last_error = "not attempted"
        for attempt in range(1, self.max_attempts + 1):
            try:
                label, confidence = parse_output(self.llm.complete(prompt, timeout=self.timeout_s).text)
                return Classification(label, confidence, attempt)
            except LLMError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if not exc.retryable:
                    return Classification(None, None, attempt, last_error)
            except InvalidOutput as exc:
                last_error = f"invalid output: {exc}"
        return Classification(None, None, self.max_attempts, last_error)
