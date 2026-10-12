"""Shared pieces for M4: the classifier error type, sample data and fake classifiers.

The real classifier is an LLM call. Tests inject plain callables ``classifier(text) -> label``
that may raise ``RetryableError`` (transient: rate limited, timeout) or any other
``Exception`` (permanent: the input is bad).
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

SAMPLE_JSONL = Path(__file__).resolve().parent / "data" / "rows.jsonl"


class RetryableError(Exception):
    """A transient classifier failure: worth another attempt."""


def keyword_label(text: str) -> str:
    lowered = text.lower()
    if any(w in lowered for w in ("broken", "terrible", "never", "refund")):
        return "negative"
    if any(w in lowered for w in ("love", "great", "works")):
        return "positive"
    return "neutral"


def flaky_classifier(fail_first: int = 1) -> Callable[[str], str]:
    """'[flaky]' texts raise RetryableError on their first ``fail_first`` attempts; '[bad]' texts always
    raise ValueError; everything else gets a keyword label. Thread-safe; ``.calls`` records every text."""
    lock = threading.Lock()
    attempts: dict[str, int] = {}
    calls: list[str] = []

    def classify(text: str) -> str:
        with lock:
            calls.append(text)
            attempts[text] = attempts.get(text, 0) + 1
            n = attempts[text]
        if "[bad]" in text:
            raise ValueError("unclassifiable input")
        if "[flaky]" in text and n <= fail_first:
            raise RetryableError(f"model overloaded (attempt {n})")
        return keyword_label(text)

    classify.calls = calls  # type: ignore[attr-defined]
    return classify
