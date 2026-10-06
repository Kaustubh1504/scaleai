"""The mock LLM engine shared by the in-process client and the HTTP server.

``plan_*`` decides everything about a call up front (fault, latency, output,
usage) under a lock, so behaviour is deterministic. The callers then wait for
the planned latency on their clock and raise or return.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import threading
from collections import deque
from dataclasses import asdict, dataclass, field

from ..fake_clock import Clock, RealClock
from ..tokens import count_tokens
from .config import CONTENT_FAULTS, FORMAT_FAULTS, STREAM_FAULTS, TRANSPORT_FAULTS, LLMConfig
from .errors import (
    ContextLengthExceededError,
    LLMBadRequestError,
    LLMError,
    LLMRateLimitError,
    LLMServerError,
    LLMTimeoutError,
)
from .responders import KeywordClassifier, Responder, ResponderContext

_RATE_FIELDS = {
    "timeout": "timeout_rate",
    "rate_limit": "rate_limit_rate",
    "server_error": "failure_rate",
    "wrong_label": "wrong_label_rate",
    "inconsistent": "inconsistent_rate",
    "tool_loop": "tool_loop_rate",
    "tool_bad_args": "tool_bad_args_rate",
    "tool_unknown": "tool_unknown_rate",
    "malformed": "malformed_rate",
    "fenced": "fenced_rate",
    "prose_wrapped": "prose_wrapped_rate",
    "stream_disconnect": "stream_disconnect_rate",
}

# Which content/format faults make sense for each kind of call.
_APPLICABLE = {
    "complete": {"wrong_label", "inconsistent", "malformed", "fenced", "prose_wrapped"},
    "stream": {"wrong_label", "inconsistent", "stream_disconnect"},
    "chat": {"tool_loop", "tool_bad_args", "tool_unknown"},
}


def default_responder() -> KeywordClassifier:
    return KeywordClassifier(
        {
            "billing": ["invoice", "charge", "charged", "refund", "payment", "billing", "subscription"],
            "bug": ["error", "crash", "broken", "bug", "fails", "exception"],
            "feature_request": ["feature", "add", "wish", "support for", "would love"],
        },
        default_label="other",
    )


@dataclass
class Usage:
    calls: int = 0
    failed_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def as_dict(self) -> dict:
        data = asdict(self)
        data["cost_usd"] = round(self.cost_usd, 6)
        return data


@dataclass
class CallRecord:
    n: int
    kind: str
    prompt_key: str
    attempt: int
    fault: str | None
    error: str | None


@dataclass
class Plan:
    n: int
    attempt: int
    fault: str | None
    latency: float
    error: LLMError | None = None
    text: str | None = None
    tool_calls: list[dict] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    disconnect_after_chunks: int | None = None


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON-encoded, like real APIs; may be malformed.


@dataclass
class ChatResponse:
    content: str | None
    tool_calls: list[ToolCall]
    input_tokens: int
    output_tokens: int
    model: str


def chunk_words(text: str, words_per_chunk: int) -> list[str]:
    """Split text into chunks of N words that concatenate back to ``text``."""
    pieces = re.findall(r"\s*\S+\s*", text) or ([text] if text else [])
    size = max(1, words_per_chunk)
    return ["".join(pieces[i : i + size]) for i in range(0, len(pieces), size)]


class MockLLMEngine:
    def __init__(self, config: LLMConfig | None = None, responder: Responder | None = None, clock: Clock | None = None):
        self.config = config or LLMConfig()
        self.responder = responder or default_responder()
        self.clock = clock or RealClock()
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._n = 0
            self._attempts: dict[str, int] = {}
            self._needle_hits: dict[str, int] = {}
            self._accepted: deque[float] = deque()
            self.usage = Usage()
            self.calls: list[CallRecord] = []

    def usage_snapshot(self) -> Usage:
        with self._lock:
            return Usage(**asdict(self.usage))

    # ------------------------------------------------------------------ planning

    def _pick_fault(self, n: int, text: str, attempt: int, rng: random.Random, kind: str) -> str | None:
        cfg = self.config
        if n in cfg.fault_script:
            fault = cfg.fault_script[n]
            return None if fault == "ok" else fault
        for needle, sequence in cfg.prompt_faults.items():
            if needle in text:
                # Counted per needle, not per exact prompt, so callers may reword retries.
                seen = self._needle_hits.get(needle, 0)
                self._needle_hits[needle] = seen + 1
                fault = sequence[seen] if seen < len(sequence) else "ok"
                return None if fault == "ok" else fault
        if attempt <= cfg.fail_first_attempts:
            return "server_error"
        applicable = _APPLICABLE[kind]
        for group in (TRANSPORT_FAULTS, CONTENT_FAULTS, FORMAT_FAULTS, STREAM_FAULTS):
            for fault in group:
                # Always draw, so adding a rate for one kind never shifts the others.
                roll = rng.random()
                if (fault in TRANSPORT_FAULTS or fault in applicable) and roll < getattr(cfg, _RATE_FIELDS[fault]):
                    return fault
        return None

    def _rate_limited(self, now: float) -> float | None:
        cfg = self.config
        if cfg.rpm_limit is None:
            return None
        while self._accepted and self._accepted[0] <= now - cfg.rate_limit_window_s:
            self._accepted.popleft()
        if len(self._accepted) >= cfg.rpm_limit:
            return max(0.001, self._accepted[0] + cfg.rate_limit_window_s - now)
        return None

    def _plan(self, kind: str, *, prompt: str, system: str | None, key_source: str, timeout: float | None,
              messages: list[dict] | None = None, tools: list[dict] | None = None) -> Plan:
        cfg = self.config
        key = hashlib.sha256(f"{kind}\x00{system or ''}\x00{key_source}".encode()).hexdigest()[:16]
        with self._lock:
            self._n += 1
            n = self._n
            attempt = self._attempts.get(key, 0) + 1
            self._attempts[key] = attempt
            rng = random.Random(f"{cfg.seed}|{key}|{attempt}")
            fault = self._pick_fault(n, key_source, attempt, rng, kind)
            latency = cfg.latency_s + rng.random() * cfg.latency_jitter_s
            input_tokens = count_tokens(system or "") + count_tokens(key_source)
            plan = Plan(n=n, attempt=attempt, fault=fault, latency=latency, input_tokens=input_tokens)

            retry_after = self._rate_limited(self.clock.time())
            if cfg.max_context_tokens is not None and input_tokens > cfg.max_context_tokens:
                plan.error = ContextLengthExceededError(input_tokens, cfg.max_context_tokens)
                plan.latency = 0.0
            elif retry_after is not None:
                plan.error = LLMRateLimitError(f"rate limit of {cfg.rpm_limit} calls per "
                                               f"{cfg.rate_limit_window_s:g}s exceeded", retry_after=retry_after)
                plan.latency = 0.0
            elif fault == "rate_limit":
                plan.error = LLMRateLimitError("rate limited", retry_after=cfg.retry_after_s)
                plan.latency = 0.0
            elif fault == "server_error":
                plan.error = LLMServerError("upstream model error", status_code=rng.choice([500, 502, 503]))
            elif fault == "timeout" or (timeout is not None and latency > timeout):
                plan.error = LLMTimeoutError(f"no response within {timeout if timeout is not None else cfg.timeout_hang_s:g}s")
                plan.latency = timeout if timeout is not None else cfg.timeout_hang_s

            if plan.error is None:
                self._accepted.append(self.clock.time())
                ctx = ResponderContext(kind=kind, prompt=prompt, system=system, attempt=attempt, rng=rng,
                                       fault=fault, messages=messages, tools=tools)
                try:
                    if kind == "chat":
                        self._fill_chat(plan, ctx, messages or [], rng)
                    else:
                        plan.text = self._format(self.responder.complete(ctx), fault, rng)
                except NotImplementedError as exc:
                    plan.error = LLMBadRequestError(str(exc))
                    plan.latency = 0.0

            if plan.error is not None:
                self.usage.failed_calls += 1
            else:
                if kind == "stream" and fault == "stream_disconnect":
                    total = len(chunk_words(plan.text or "", cfg.stream_chunk_words))
                    plan.disconnect_after_chunks = rng.randrange(max(1, total))
                plan.output_tokens = count_tokens(plan.text or "") + sum(
                    count_tokens(c["name"]) + count_tokens(c["arguments"]) for c in plan.tool_calls)
                self.usage.calls += 1
                self.usage.input_tokens += plan.input_tokens
                self.usage.output_tokens += plan.output_tokens
                self.usage.cost_usd += (plan.input_tokens * cfg.input_cost_per_1k
                                        + plan.output_tokens * cfg.output_cost_per_1k) / 1000
            self.calls.append(CallRecord(n, kind, key, attempt, fault,
                                         type(plan.error).__name__ if plan.error else None))
            return plan

    @staticmethod
    def _format(text: str, fault: str | None, rng: random.Random) -> str:
        if fault == "fenced":
            return f"```json\n{text}\n```"
        if fault == "prose_wrapped":
            return f"Sure! Here is the result:\n{text}\nLet me know if you need anything else."
        if fault == "malformed":
            if rng.random() < 0.5:
                return text[: max(1, (len(text) * 2) // 3)]
            return text.replace('"', "'")
        return text

    def _fill_chat(self, plan: Plan, ctx: ResponderContext, messages: list[dict], rng: random.Random) -> None:
        if ctx.fault == "tool_loop":
            previous = next((m for m in reversed(messages) if m.get("role") == "assistant" and m.get("tool_calls")), None)
            if previous is not None:
                plan.tool_calls = [{"name": c["name"], "arguments": c["arguments"]
                                    if isinstance(c["arguments"], str) else json.dumps(c["arguments"])}
                                   for c in previous["tool_calls"]]
                return
        answer = self.responder.chat(ctx)
        plan.text = answer.get("content")
        calls = []
        for call in answer.get("tool_calls") or []:
            name, args = call["name"], json.dumps(call.get("arguments", {}), sort_keys=True)
            if ctx.fault == "tool_unknown":
                name = f"{name}_v2"
            elif ctx.fault == "tool_bad_args":
                args = args[: max(1, len(args) // 2)]
            calls.append({"name": name, "arguments": args})
        plan.tool_calls = calls

    def plan_complete(self, prompt: str, system: str | None = None, timeout: float | None = None) -> Plan:
        return self._plan("complete", prompt=prompt, system=system, key_source=prompt, timeout=timeout)

    def plan_stream(self, prompt: str, system: str | None = None, timeout: float | None = None) -> Plan:
        return self._plan("stream", prompt=prompt, system=system, key_source=prompt, timeout=timeout)

    def plan_chat(self, messages: list[dict], tools: list[dict] | None = None, timeout: float | None = None) -> Plan:
        key_source = json.dumps(messages, sort_keys=True, default=str)
        return self._plan("chat", prompt=key_source, system=None, key_source=key_source, timeout=timeout,
                          messages=messages, tools=tools)

    # ------------------------------------------------------------------ results

    def response_for(self, plan: Plan) -> LLMResponse:
        return LLMResponse(plan.text or "", plan.input_tokens, plan.output_tokens, self.config.model)

    def chat_response_for(self, plan: Plan) -> ChatResponse:
        calls = [ToolCall(id=f"call_{plan.n}_{i}", name=c["name"], arguments=c["arguments"])
                 for i, c in enumerate(plan.tool_calls)]
        return ChatResponse(plan.text, calls, plan.input_tokens, plan.output_tokens, self.config.model)

    def stream_chunks(self, plan: Plan) -> tuple[list[str], bool]:
        """The chunks to emit and whether the stream completes normally."""
        chunks = chunk_words(plan.text or "", self.config.stream_chunk_words)
        if plan.disconnect_after_chunks is not None:
            return chunks[: plan.disconnect_after_chunks], False
        return chunks, True
