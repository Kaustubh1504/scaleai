"""In-process mock LLM client. Same interface as ``HTTPLLMClient``.

    client = MockLLMClient(LLMConfig(seed=7, failure_rate=0.2))
    resp = client.complete("Classify: <item>I was charged twice</item>")
    resp.text  # '{"label": "billing", "confidence": 0.93}'

Errors are raised as subclasses of ``LLMError`` (see ``errors.py``).
Latency and timeouts elapse on the client's clock, so a ``FakeClock`` makes
everything instant.
"""

from __future__ import annotations

from typing import AsyncIterator, Iterator

from ..fake_clock import Clock, aelapse, elapse
from .config import LLMConfig
from .engine import ChatResponse, CallRecord, LLMResponse, MockLLMEngine, Usage
from .errors import LLMStreamInterruptedError
from .responders import Responder


class MockLLMClient:
    def __init__(
        self,
        config: LLMConfig | None = None,
        *,
        responder: Responder | None = None,
        clock: Clock | None = None,
        engine: MockLLMEngine | None = None,
    ):
        self.engine = engine or MockLLMEngine(config, responder, clock)

    @property
    def config(self) -> LLMConfig:
        return self.engine.config

    @property
    def usage(self) -> Usage:
        """Snapshot of token/cost counters across all calls made through this engine."""
        return self.engine.usage_snapshot()

    @property
    def calls(self) -> list[CallRecord]:
        return list(self.engine.calls)

    def reset(self) -> None:
        self.engine.reset()

    # ------------------------------------------------------------- completion

    def complete(self, prompt: str, *, system: str | None = None, timeout: float | None = None) -> LLMResponse:
        plan = self.engine.plan_complete(prompt, system, timeout)
        elapse(self.engine.clock, plan.latency)
        if plan.error is not None:
            raise plan.error
        return self.engine.response_for(plan)

    async def acomplete(self, prompt: str, *, system: str | None = None, timeout: float | None = None) -> LLMResponse:
        plan = self.engine.plan_complete(prompt, system, timeout)
        await aelapse(self.engine.clock, plan.latency)
        if plan.error is not None:
            raise plan.error
        return self.engine.response_for(plan)

    # ------------------------------------------------------------- tool calling

    def chat(self, messages: list[dict], *, tools: list[dict] | None = None,
             timeout: float | None = None) -> ChatResponse:
        plan = self.engine.plan_chat(messages, tools, timeout)
        elapse(self.engine.clock, plan.latency)
        if plan.error is not None:
            raise plan.error
        return self.engine.chat_response_for(plan)

    async def achat(self, messages: list[dict], *, tools: list[dict] | None = None,
                    timeout: float | None = None) -> ChatResponse:
        plan = self.engine.plan_chat(messages, tools, timeout)
        await aelapse(self.engine.clock, plan.latency)
        if plan.error is not None:
            raise plan.error
        return self.engine.chat_response_for(plan)

    # ------------------------------------------------------------- streaming

    def stream(self, prompt: str, *, system: str | None = None, timeout: float | None = None) -> Iterator[str]:
        """Yield text chunks. Raises ``LLMStreamInterruptedError`` if the stream drops."""
        plan = self.engine.plan_stream(prompt, system, timeout)
        elapse(self.engine.clock, plan.latency)
        if plan.error is not None:
            raise plan.error
        chunks, completed = self.engine.stream_chunks(plan)
        for chunk in chunks:
            elapse(self.engine.clock, self.config.stream_chunk_delay_s)
            yield chunk
        if not completed:
            raise LLMStreamInterruptedError("stream ended before completion")

    async def astream(self, prompt: str, *, system: str | None = None,
                      timeout: float | None = None) -> AsyncIterator[str]:
        plan = self.engine.plan_stream(prompt, system, timeout)
        await aelapse(self.engine.clock, plan.latency)
        if plan.error is not None:
            raise plan.error
        chunks, completed = self.engine.stream_chunks(plan)
        for chunk in chunks:
            await aelapse(self.engine.clock, self.config.stream_chunk_delay_s)
            yield chunk
        if not completed:
            raise LLMStreamInterruptedError("stream ended before completion")
