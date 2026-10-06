import asyncio

TRANSIENT = {429, 500, 502, 503, 504}


def retry_delay(response, attempt, backoff_seconds):
    header = response.headers.get("Retry-After")
    if header is not None:
        return float(header)
    return backoff_seconds * 2 ** attempt


async def send_with_retries(call, max_retries, backoff_seconds):
    """Await call() until it returns a final response. Returns (response, attempts)."""
    attempts = 0
    while True:
        response = await call()
        attempts += 1
        if response.status not in TRANSIENT or attempts > max_retries:
            return response, attempts
        await asyncio.sleep(retry_delay(response, attempts - 1, backoff_seconds))
