"""Classify one ticket with the LLM: prompt, parse, validate, retry with backoff."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass

from mock_services.clock import Clock
from mock_services.llm import LABELS
from shared.mock_llm import LLMError, LLMRateLimitError

PROMPT = """You are a support triage assistant. Classify the support ticket into exactly one label.
Allowed labels: {labels}.
Respond with only a JSON object: {{"label": "<label>", "confidence": <number between 0 and 1>}}.

<item>{subject}
{body}</item>"""


class InvalidOutput(ValueError):
    pass


def build_prompt(ticket: dict) -> str:
    return PROMPT.format(labels=", ".join(LABELS), subject=ticket["subject"], body=ticket["body"])


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        text = text[first_newline + 1 :] if first_newline != -1 else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def parse_output(text: str) -> tuple[str, float]:
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


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_s: float = 0.5
    max_delay_s: float = 8.0
    timeout_s: float = 10.0

    def backoff(self, attempt: int, rng: random.Random) -> float:
        """Delay after failed attempt ``attempt`` (1-based): equal jitter on an exponential base."""
        ceiling = min(self.max_delay_s, self.base_delay_s * 2 ** (attempt - 1))
        return rng.uniform(ceiling / 2, ceiling)


def _result(ticket_id: str, attempts: int, *, label: str | None = None, confidence: float | None = None,
            error: str | None = None) -> dict:
    return {
        "ticket_id": ticket_id,
        "status": "failed" if error else "classified",
        "label": label,
        "confidence": confidence,
        "attempts": attempts,
        "error": error,
    }


class TicketClassifier:
    def __init__(self, llm, clock: Clock, policy: RetryPolicy = RetryPolicy(), rng: random.Random | None = None):
        self.llm = llm
        self.clock = clock
        self.policy = policy
        self.rng = rng or random.Random()

    def classify(self, ticket: dict) -> dict:
        prompt = build_prompt(ticket)
        last_error = "not attempted"
        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                response = self.llm.complete(prompt, timeout=self.policy.timeout_s)
                label, confidence = parse_output(response.text)
                return _result(ticket["ticket_id"], attempt, label=label, confidence=confidence)
            except LLMRateLimitError as exc:
                last_error, wait = f"rate limited: {exc}", exc.retry_after
            except LLMError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if not exc.retryable:
                    return _result(ticket["ticket_id"], attempt, error=last_error)
                wait = self.policy.backoff(attempt, self.rng)
            except InvalidOutput as exc:
                last_error, wait = f"invalid output: {exc}", self.policy.backoff(attempt, self.rng)
            if attempt < self.policy.max_attempts:
                self.clock.sleep(wait)
        return _result(ticket["ticket_id"], self.policy.max_attempts, error=last_error)
