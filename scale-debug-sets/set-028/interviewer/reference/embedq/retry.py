import asyncio
from dataclasses import dataclass

RETRYABLE = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int
    backoff_seconds: float


# VERIFIED
def wait_time(response, policy, attempt):
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        return float(retry_after)
    return policy.backoff_seconds * (2 ** attempt)


async def send_with_retries(do_request, policy, sleep=asyncio.sleep):
    response = None
    for attempt in range(policy.max_retries + 1):
        response = await do_request()
        if response.status not in RETRYABLE:
            return response
        if attempt < policy.max_retries:
            await sleep(wait_time(response, policy, attempt))
    return response
