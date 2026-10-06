import asyncio

RETRYABLE = {429, 500, 502, 503, 504}


# VERIFIED
def backoff_delay(response, attempt, base):
    """Seconds to wait after failed attempt number `attempt` (the first attempt is 1)."""
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        return float(retry_after)
    return base * 2 ** (attempt - 1)


async def with_retries(call, max_retries, base):
    """Await call() until it returns a non-retryable response or attempts run out.
    Returns (response, attempts)."""
    attempt = 0
    while True:
        attempt += 1
        response = await call()
        if response.status not in RETRYABLE or attempt > max_retries:
            return response, attempt
        asyncio.sleep(backoff_delay(response, attempt, base))
