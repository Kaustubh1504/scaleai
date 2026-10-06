"""HTTP clients for the mock LLM server, with the same interface as ``MockLLMClient``.

    client = HTTPLLMClient("http://127.0.0.1:8001")
    client.complete("<item>The app crashes on login</item>").text

Pass ``http=`` to reuse an existing ``httpx.Client`` (for example FastAPI's
``TestClient(create_app())`` in tests, which needs no network).
"""

from __future__ import annotations

import json
from typing import AsyncIterator, Iterator

import httpx

from .engine import ChatResponse, LLMResponse, ToolCall
from .errors import (
    ContextLengthExceededError,
    LLMBadRequestError,
    LLMError,
    LLMRateLimitError,
    LLMServerError,
    LLMStreamInterruptedError,
    LLMTimeoutError,
)


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    try:
        error = response.json().get("error", {})
    except (ValueError, AttributeError):
        error = {}
    message = error.get("message") or response.text
    status = response.status_code
    if status == 429:
        retry_after = error.get("retry_after")
        if retry_after is None:
            retry_after = float(response.headers.get("Retry-After", "1"))
        raise LLMRateLimitError(message, retry_after=float(retry_after))
    if status == 504:
        raise LLMTimeoutError(message)
    if status == 400 and error.get("code") == "context_length_exceeded":
        raise ContextLengthExceededError(error.get("tokens", 0), error.get("limit", 0), message=message)
    if 400 <= status < 500:
        raise LLMBadRequestError(f"HTTP {status}: {message}")
    raise LLMServerError(message, status_code=status)


def _completion(data: dict) -> LLMResponse:
    usage = data.get("usage", {})
    return LLMResponse(data["text"], usage.get("input_tokens", 0), usage.get("output_tokens", 0), data.get("model", ""))


def _chat(data: dict) -> ChatResponse:
    message, usage = data["message"], data.get("usage", {})
    calls = [ToolCall(c["id"], c["name"], c["arguments"]) for c in message.get("tool_calls") or []]
    return ChatResponse(message.get("content"), calls, usage.get("input_tokens", 0),
                        usage.get("output_tokens", 0), data.get("model", ""))


def _parse_sse(lines: Iterator[str]) -> Iterator[tuple[str, dict]]:
    event, data = "message", []
    for line in lines:
        if line == "":
            if data:
                yield event, json.loads("\n".join(data))
            event, data = "message", []
        elif line.startswith("event:"):
            event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data.append(line[len("data:"):].strip())
    if data:
        yield event, json.loads("\n".join(data))


class HTTPLLMClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8001", *, timeout: float = 30.0,
                 http: httpx.Client | None = None):
        self.timeout = timeout
        self._http = http or httpx.Client(base_url=base_url)

    def _post(self, path: str, payload: dict, timeout: float | None) -> httpx.Response:
        limit = timeout if timeout is not None else self.timeout
        try:
            response = self._http.post(path, json={**payload, "timeout": limit}, timeout=limit)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"no response within {limit:g}s") from exc
        except httpx.TransportError as exc:
            raise LLMServerError(f"connection error: {exc}", status_code=503) from exc
        _raise_for_status(response)
        return response

    def complete(self, prompt: str, *, system: str | None = None, timeout: float | None = None) -> LLMResponse:
        return _completion(self._post("/v1/complete", {"prompt": prompt, "system": system}, timeout).json())

    def chat(self, messages: list[dict], *, tools: list[dict] | None = None,
             timeout: float | None = None) -> ChatResponse:
        return _chat(self._post("/v1/chat", {"messages": messages, "tools": tools}, timeout).json())

    def stream(self, prompt: str, *, system: str | None = None, timeout: float | None = None) -> Iterator[str]:
        limit = timeout if timeout is not None else self.timeout
        try:
            with self._http.stream("POST", "/v1/stream", json={"prompt": prompt, "system": system},
                                   timeout=limit) as response:
                if response.status_code >= 400:
                    response.read()
                    _raise_for_status(response)
                done = False
                for event, data in _parse_sse(response.iter_lines()):
                    if event == "delta":
                        yield data["text"]
                    elif event == "done":
                        done = True
                if not done:
                    raise LLMStreamInterruptedError("stream ended before the done event")
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"no response within {limit:g}s") from exc
        except httpx.TransportError as exc:
            raise LLMStreamInterruptedError(f"connection dropped: {exc}") from exc

    def usage(self) -> dict:
        return self._http.get("/v1/usage").json()


class AsyncHTTPLLMClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8001", *, timeout: float = 30.0,
                 http: httpx.AsyncClient | None = None):
        self.timeout = timeout
        self._http = http or httpx.AsyncClient(base_url=base_url)

    async def _post(self, path: str, payload: dict, timeout: float | None) -> httpx.Response:
        limit = timeout if timeout is not None else self.timeout
        try:
            response = await self._http.post(path, json={**payload, "timeout": limit}, timeout=limit)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"no response within {limit:g}s") from exc
        except httpx.TransportError as exc:
            raise LLMServerError(f"connection error: {exc}", status_code=503) from exc
        _raise_for_status(response)
        return response

    async def acomplete(self, prompt: str, *, system: str | None = None,
                        timeout: float | None = None) -> LLMResponse:
        return _completion((await self._post("/v1/complete", {"prompt": prompt, "system": system}, timeout)).json())

    async def achat(self, messages: list[dict], *, tools: list[dict] | None = None,
                    timeout: float | None = None) -> ChatResponse:
        return _chat((await self._post("/v1/chat", {"messages": messages, "tools": tools}, timeout)).json())

    async def astream(self, prompt: str, *, system: str | None = None,
                      timeout: float | None = None) -> AsyncIterator[str]:
        limit = timeout if timeout is not None else self.timeout
        try:
            async with self._http.stream("POST", "/v1/stream", json={"prompt": prompt, "system": system},
                                         timeout=limit) as response:
                if response.status_code >= 400:
                    await response.aread()
                    _raise_for_status(response)
                done = False
                event, data = "message", []
                async for line in response.aiter_lines():
                    if line.startswith("event:"):
                        event = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        data.append(line[len("data:"):].strip())
                    elif line == "" and data:
                        payload = json.loads("\n".join(data))
                        if event == "delta":
                            yield payload["text"]
                        elif event == "done":
                            done = True
                        event, data = "message", []
                if not done:
                    raise LLMStreamInterruptedError("stream ended before the done event")
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"no response within {limit:g}s") from exc
        except httpx.TransportError as exc:
            raise LLMStreamInterruptedError(f"connection dropped: {exc}") from exc

    async def aclose(self) -> None:
        await self._http.aclose()


__all__ = ["HTTPLLMClient", "AsyncHTTPLLMClient", "LLMError"]
