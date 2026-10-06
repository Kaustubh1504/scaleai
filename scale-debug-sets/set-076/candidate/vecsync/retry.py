import asyncio

RETRYABLE = frozenset({429, 500, 502, 503, 504})


def parse_retry_after(headers):
    for key, value in headers.items():
        if key.lower() == "retry-after":
            try:
                return max(0.0, float(value))
            except ValueError:
                return None
    return None


def backoff_delay(response, attempt, base):
    return parse_retry_after(response.headers) or base * (2 ** attempt)


async def send_with_retries(do_request, max_retries, base, sleep=asyncio.sleep):
    response = None
    for attempt in range(max_retries):
        response = await do_request()
        if response.status not in RETRYABLE:
            return response
        if attempt < max_retries:
            await sleep(backoff_delay(response, attempt, base))
    return response
