# 33. Async retries and gathers that don't hide failures
# Standalone: copy this file as-is. Deps: stdlib + httpx

import asyncio

import httpx


async def arequest_with_retries(client: httpx.AsyncClient, method: str, url: str, *,
                                retries: int = 3, backoff: float = 0.5, **kwargs):
    """Async request_with_retries. Uses `await asyncio.sleep`: time.sleep would freeze every coroutine.
    Returns the first non-retryable Response (2xx or other 4xx), or None after all attempts failed."""
    kwargs.setdefault("timeout", 10)
    for attempt in range(retries + 1):
        if attempt:
            await asyncio.sleep(backoff * 2 ** (attempt - 1))
        try:
            r = await client.request(method, url, **kwargs)
        except httpx.TransportError:
            continue
        if r.status_code != 429 and r.status_code < 500:
            return r
    return None


async def gather_bounded_safe(fn, items, limit: int = 5) -> list:
    """await fn(item) for every item, at most `limit` at once, results in input order.
    A failure becomes the exception object in its slot (check isinstance(x, Exception)) instead of
    discarding everyone else's results."""
    sem = asyncio.Semaphore(limit)

    async def run(item):
        async with sem:                     # the semaphore must wrap the awaited call itself
            return await fn(item)

    return await asyncio.gather(*(run(i) for i in items), return_exceptions=True)
