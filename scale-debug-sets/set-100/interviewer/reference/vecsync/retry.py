from dataclasses import dataclass

RETRYABLE = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int
    backoff_seconds: float


def backoff(headers, attempt, policy):
    retry_after = (headers or {}).get("Retry-After")
    if retry_after is not None:
        return float(retry_after)
    return policy.backoff_seconds * (2 ** attempt)


async def send_with_retries(send, policy, sleep, on_attempt=None):
    """Call `send()` until it returns a non-retryable status or the retries run out."""
    for attempt in range(policy.max_retries + 1):
        if on_attempt is not None:
            on_attempt(attempt + 1)
        status, headers, body = await send()
        if status not in RETRYABLE:
            break
        if attempt < policy.max_retries:
            await sleep(backoff(headers, attempt, policy))
    return status, headers, body
