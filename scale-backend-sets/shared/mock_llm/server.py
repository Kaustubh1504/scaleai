"""HTTP server for the mock LLM.

Endpoints
---------
POST /v1/complete   {"prompt", "system"?, "timeout"?}
    200 {"text", "model", "usage": {"input_tokens", "output_tokens"}}
POST /v1/chat       {"messages", "tools"?, "timeout"?}
    200 {"message": {"content", "tool_calls": [{"id", "name", "arguments"}]}, "model", "usage"}
POST /v1/stream     {"prompt", "system"?}
    200 text/event-stream:  "event: delta / data: {"text": ...}" repeated, then
                            "event: done / data: {"usage": ...}".
    A dropped stream simply ends without the done event.
GET  /v1/usage            token and cost counters
POST /v1/admin/reset      clear counters and attempt history
PATCH /v1/admin/config    change LLMConfig fields at runtime (e.g. {"failure_rate": 0.3})
GET  /health

Errors: 400 bad request / context length, 429 with a Retry-After header,
500/502/503 upstream error, 504 timeout. Bodies are {"error": {"type", "message"}}.
"""

from __future__ import annotations

import json
import math
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from ..fake_clock import aelapse
from .engine import MockLLMEngine, Plan
from .errors import ContextLengthExceededError, LLMError, LLMRateLimitError


class CompleteBody(BaseModel):
    prompt: str
    system: str | None = None
    timeout: float | None = None


class ChatBody(BaseModel):
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None = None
    timeout: float | None = None


def error_response(error: LLMError) -> JSONResponse:
    status = error.status_code or 500
    headers = {}
    body: dict[str, Any] = {"type": type(error).__name__, "message": str(error)}
    if isinstance(error, LLMRateLimitError):
        headers["Retry-After"] = str(max(1, math.ceil(error.retry_after)))
        body["retry_after"] = error.retry_after
    if isinstance(error, ContextLengthExceededError):
        body.update(code="context_length_exceeded", tokens=error.tokens, limit=error.limit)
    return JSONResponse({"error": body}, status_code=status, headers=headers)


def _usage(plan: Plan) -> dict:
    return {"input_tokens": plan.input_tokens, "output_tokens": plan.output_tokens}


def create_app(engine: MockLLMEngine | None = None) -> FastAPI:
    engine = engine or MockLLMEngine()
    app = FastAPI(title="Mock LLM")
    app.state.engine = engine

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "model": engine.config.model}

    @app.post("/v1/complete")
    async def complete(body: CompleteBody):
        plan = engine.plan_complete(body.prompt, body.system, body.timeout)
        await aelapse(engine.clock, plan.latency)
        if plan.error is not None:
            return error_response(plan.error)
        return {"text": plan.text, "model": engine.config.model, "usage": _usage(plan)}

    @app.post("/v1/chat")
    async def chat(body: ChatBody):
        plan = engine.plan_chat(body.messages, body.tools, body.timeout)
        await aelapse(engine.clock, plan.latency)
        if plan.error is not None:
            return error_response(plan.error)
        response = engine.chat_response_for(plan)
        return {
            "message": {
                "content": response.content,
                "tool_calls": [{"id": c.id, "name": c.name, "arguments": c.arguments} for c in response.tool_calls],
            },
            "model": response.model,
            "usage": _usage(plan),
        }

    @app.post("/v1/stream")
    async def stream(body: CompleteBody):
        plan = engine.plan_stream(body.prompt, body.system, body.timeout)
        await aelapse(engine.clock, plan.latency)
        if plan.error is not None:
            return error_response(plan.error)
        chunks, completed = engine.stream_chunks(plan)

        async def events():
            for chunk in chunks:
                await aelapse(engine.clock, engine.config.stream_chunk_delay_s)
                yield f"event: delta\ndata: {json.dumps({'text': chunk})}\n\n"
            if completed:
                yield f"event: done\ndata: {json.dumps({'usage': _usage(plan)})}\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    @app.get("/v1/usage")
    def usage() -> dict:
        return engine.usage_snapshot().as_dict()

    @app.post("/v1/admin/reset")
    def reset() -> dict:
        engine.reset()
        return {"status": "reset"}

    @app.patch("/v1/admin/config")
    def patch_config(changes: dict[str, Any]) -> dict:
        try:
            engine.config.update(**changes)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return engine.config.as_dict()

    return app
