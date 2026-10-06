"""Exceptions raised by every mock LLM client (in-process and HTTP).

Catch ``LLMError`` for everything; check ``.retryable`` to decide whether a
retry can help.
"""

from __future__ import annotations


class LLMError(Exception):
    retryable = False
    status_code: int | None = None

    def __init__(self, message: str = ""):
        super().__init__(message or self.__class__.__name__)


class LLMTimeoutError(LLMError):
    """The call did not finish within the timeout (HTTP 504 or client timeout)."""

    retryable = True
    status_code = 504


class LLMRateLimitError(LLMError):
    """HTTP 429. ``retry_after`` is the number of seconds the server asked for."""

    retryable = True
    status_code = 429

    def __init__(self, message: str = "rate limited", retry_after: float = 1.0):
        super().__init__(message)
        self.retry_after = retry_after


class LLMServerError(LLMError):
    """HTTP 5xx or a dropped connection."""

    retryable = True

    def __init__(self, message: str = "internal server error", status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class LLMBadRequestError(LLMError):
    """HTTP 400. Retrying the same request will fail again."""

    retryable = False
    status_code = 400


class ContextLengthExceededError(LLMBadRequestError):
    def __init__(self, tokens: int, limit: int, message: str | None = None):
        super().__init__(message or f"prompt has {tokens} tokens; limit is {limit}")
        self.tokens = tokens
        self.limit = limit


class LLMStreamInterruptedError(LLMError):
    """A streaming response ended before its final ``done`` event."""

    retryable = True
