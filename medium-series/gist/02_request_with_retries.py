# 02. Any HTTP call with retries
# Standalone: copy this file as-is. Deps: stdlib + httpx

import time

import httpx


def request_with_retries(method: str, url: str, *, retries: int = 3, backoff: float = 0.5,
                         client=None, **kwargs):
    """Retry 429 / 5xx / timeouts / connection errors with exponential backoff.

    Returns the first non-retryable Response (2xx or another 4xx) for you to judge,
    or None if every attempt failed. kwargs go to httpx: json=, params=, headers=, content=, timeout=
    """
    http = client or httpx.Client()
    kwargs.setdefault("timeout", 10)
    try:
        for attempt in range(retries + 1):
            if attempt:
                time.sleep(backoff * 2 ** (attempt - 1))
            try:
                r = http.request(method, url, **kwargs)
            except httpx.TransportError:
                continue
            if r.status_code != 429 and r.status_code < 500:
                return r
        return None
    finally:
        if client is None:
            http.close()
