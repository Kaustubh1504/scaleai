"""Responders decide what the mock model *would* say if nothing went wrong.

The engine handles latency, errors and format faults; a responder only maps a
request to clean output, honouring content faults (``ctx.fault``) it supports.

Prompt conventions understood by the built-in responders (problems document
these in their PART files):

* Single item: put the text in ``<item>...</item>``. Text outside the tags
  (your instructions) is ignored. Without tags the whole prompt is used.
* Batch: put a JSON array of ``{"id": ..., "text": ...}`` objects in
  ``<items>...</items>``. The answer is a JSON array in the same order.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass, field
from typing import Any, Callable

ITEM_RE = re.compile(r"<item>(.*?)</item>", re.S)
ITEMS_RE = re.compile(r"<items>(.*?)</items>", re.S)


@dataclass
class ResponderContext:
    kind: str  # "complete" | "chat" | "stream"
    prompt: str
    system: str | None
    attempt: int
    rng: random.Random
    fault: str | None = None
    messages: list[dict] | None = None
    tools: list[dict] | None = None


class Responder:
    def complete(self, ctx: ResponderContext) -> str:
        raise NotImplementedError(f"{type(self).__name__} does not support text completion")

    def chat(self, ctx: ResponderContext) -> dict:
        """Return {"content": str | None, "tool_calls": [{"name": str, "arguments": dict}]}."""
        raise NotImplementedError(f"{type(self).__name__} does not support chat/tool calling")


def stable_fraction(text: str) -> float:
    """A deterministic number in [0, 1) derived from ``text``."""
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16) / 0x1_0000_0000


def extract_item(prompt: str) -> str:
    match = ITEM_RE.search(prompt)
    return match.group(1).strip() if match else prompt


def extract_items(prompt: str) -> list[dict] | None:
    match = ITEMS_RE.search(prompt)
    if not match:
        return None
    try:
        items = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(items, list) or not all(isinstance(i, dict) and "id" in i for i in items):
        return None
    return items


class KeywordClassifier(Responder):
    """Classifies text by keyword hits.

    The label with the most keyword hits wins (whole words, also matching the
    suffixes s/es/ed/ing, so "crash" matches "crashes"); ties go to the label
    listed first. No hits gives ``default_label``. Confidence is deterministic
    per text: 0.70-0.99 for a clear winner, 0.50-0.69 for a tie, 0.30-0.49
    when no keyword matched.

    Output (single): ``{"label": "...", "confidence": 0.87}``
    Output (batch):  ``[{"id": ..., "label": "...", "confidence": 0.87}, ...]``
    """

    def __init__(self, keywords: dict[str, list[str]], default_label: str, label_field: str = "label"):
        self.keywords = keywords
        self.default_label = default_label
        self.label_field = label_field
        self._patterns = {
            label: [re.compile(rf"\b{re.escape(k.lower())}(?:s|es|ed|ing)?\b") for k in kws]
            for label, kws in keywords.items()
        }

    @property
    def labels(self) -> list[str]:
        labels = list(self.keywords)
        if self.default_label not in labels:
            labels.append(self.default_label)
        return labels

    def classify(self, text: str) -> tuple[str, float]:
        lowered = text.lower()
        scores = {label: sum(len(p.findall(lowered)) for p in pats) for label, pats in self._patterns.items()}
        best = max(scores.values(), default=0)
        frac = stable_fraction(text)
        if best == 0:
            return self.default_label, round(0.30 + 0.19 * frac, 2)
        winners = [label for label, score in scores.items() if score == best]
        if len(winners) > 1:
            return winners[0], round(0.50 + 0.19 * frac, 2)
        return winners[0], round(0.70 + 0.29 * frac, 2)

    def _apply_fault(self, label: str, fault: str | None, rng: random.Random) -> str:
        if fault == "wrong_label":
            return rng.choice(["unknown", "N/A", f"{label.title()} Issue"])
        if fault == "inconsistent":
            others = [lbl for lbl in self.labels if lbl != label]
            return rng.choice(others) if others else label
        return label

    def complete(self, ctx: ResponderContext) -> str:
        items = extract_items(ctx.prompt)
        if items is not None:
            results = []
            for item in items:
                label, confidence = self.classify(str(item.get("text", "")))
                results.append({"id": item["id"], self.label_field: label, "confidence": confidence})
            if results and ctx.fault in ("wrong_label", "inconsistent"):
                victim = results[ctx.rng.randrange(len(results))]
                victim[self.label_field] = self._apply_fault(victim[self.label_field], ctx.fault, ctx.rng)
            return json.dumps(results)
        label, confidence = self.classify(extract_item(ctx.prompt))
        label = self._apply_fault(label, ctx.fault, ctx.rng)
        return json.dumps({self.label_field: label, "confidence": confidence})


class FunctionResponder(Responder):
    """Wrap plain functions: ``complete_fn(ctx) -> str`` and/or ``chat_fn(ctx) -> dict``."""

    def __init__(
        self,
        complete_fn: Callable[[ResponderContext], str] | None = None,
        chat_fn: Callable[[ResponderContext], dict] | None = None,
    ):
        self._complete_fn = complete_fn
        self._chat_fn = chat_fn

    def complete(self, ctx: ResponderContext) -> str:
        if self._complete_fn is None:
            return super().complete(ctx)
        return self._complete_fn(ctx)

    def chat(self, ctx: ResponderContext) -> dict:
        if self._chat_fn is None:
            return super().chat(ctx)
        return self._chat_fn(ctx)


class SummarizeResponder(Responder):
    """Returns the first ``max_words`` words of the item text, prefixed with "Summary: "."""

    def __init__(self, max_words: int = 25):
        self.max_words = max_words

    def complete(self, ctx: ResponderContext) -> str:
        words = extract_item(ctx.prompt).split()
        return "Summary: " + " ".join(words[: self.max_words])


@dataclass
class ToolStep:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class FinalStep:
    content: str


Step = ToolStep | FinalStep | Callable[[ResponderContext, list[dict]], "ToolStep | FinalStep"]


class ScriptedAgent(Responder):
    """A tool-calling model that follows a script.

    ``scripts`` maps a substring of the first user message to a list of steps.
    The step used is the number of ``tool`` messages already in the history, so
    the model advances one step per tool result it has seen. A step may be a
    callable ``(ctx, history) -> ToolStep | FinalStep`` to react to tool output.
    Running past the end of the script gives a final answer saying it gave up.
    """

    def __init__(self, scripts: dict[str, list[Step]], fallback: str = "I could not complete the task."):
        self.scripts = scripts
        self.fallback = fallback

    def chat(self, ctx: ResponderContext) -> dict:
        history = ctx.messages or []
        first_user = next((m.get("content") or "" for m in history if m.get("role") == "user"), "")
        steps = next((s for key, s in self.scripts.items() if key in first_user), None)
        if steps is None:
            return {"content": self.fallback, "tool_calls": []}
        index = sum(1 for m in history if m.get("role") == "tool")
        if index >= len(steps):
            return {"content": self.fallback, "tool_calls": []}
        step = steps[index]
        if callable(step) and not isinstance(step, (ToolStep, FinalStep)):
            step = step(ctx, history)
        if isinstance(step, FinalStep):
            return {"content": step.content, "tool_calls": []}
        return {"content": None, "tool_calls": [{"name": step.name, "arguments": dict(step.arguments)}]}
