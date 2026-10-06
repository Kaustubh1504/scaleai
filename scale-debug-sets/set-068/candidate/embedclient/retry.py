import asyncio

TRANSIENT = {429, 500, 502, 503, 504}


# VERIFIED
def retry_delay(response, attempt, backoff_s):
    header = {k.lower(): v for k, v in response.headers.items()}.get("retry-after")
    if header is not None:
        return float(header)
    return backoff_s * 2 ** attempt


async def send_with_retries(send, max_retries, backoff_s):
    """Call `send()` until it returns a non-transient status or retries run out.

    Returns (last response, number of attempts made).
    """
    attempts = 0
    for attempt in range(max_retries):
        response = await send()
        attempts += 1
        if response.status not in TRANSIENT or attempt == max_retries:
            break
        asyncio.sleep(retry_delay(response, attempt, backoff_s))
    return response, attempts
