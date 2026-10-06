"""Deterministic, fault-injecting mock LLM (in-process client + HTTP server).

See ``shared/README.md`` for the full behaviour reference.
"""

from .client import MockLLMClient
from .config import ALL_FAULTS, LLMConfig
from .engine import CallRecord, ChatResponse, LLMResponse, MockLLMEngine, ToolCall, Usage, default_responder
from .errors import (
    ContextLengthExceededError,
    LLMBadRequestError,
    LLMError,
    LLMRateLimitError,
    LLMServerError,
    LLMStreamInterruptedError,
    LLMTimeoutError,
)
from .http_client import AsyncHTTPLLMClient, HTTPLLMClient
from .responders import (
    FinalStep,
    FunctionResponder,
    KeywordClassifier,
    Responder,
    ResponderContext,
    ScriptedAgent,
    SummarizeResponder,
    ToolStep,
    extract_item,
    extract_items,
    stable_fraction,
)
from .server import create_app

__all__ = [
    "ALL_FAULTS", "AsyncHTTPLLMClient", "CallRecord", "ChatResponse", "ContextLengthExceededError",
    "FinalStep", "FunctionResponder", "HTTPLLMClient", "KeywordClassifier", "LLMBadRequestError",
    "LLMConfig", "LLMError", "LLMRateLimitError", "LLMResponse", "LLMServerError",
    "LLMStreamInterruptedError", "LLMTimeoutError", "MockLLMClient", "MockLLMEngine", "Responder",
    "ResponderContext", "ScriptedAgent", "SummarizeResponder", "ToolCall", "ToolStep", "Usage",
    "create_app", "default_responder", "extract_item", "extract_items", "stable_fraction",
]
