from dataclasses import dataclass

RETRYABLE = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int
    backoff_seconds: float


def retry_delay(response, retries_done, policy):
    """Retry-After (seconds) wins; otherwise exponential backoff from the policy base."""
    hint = response.headers.get("retry-after")
    if hint is not None:
        return float(hint)
    return policy.backoff_seconds * (2 ** retries_done)


async def with_retries(attempt, policy, sleep):
    """Run `attempt(n)` (n = 1, 2, ...) until a non-retryable status or the retries run out.

    Returns the last response and how many attempts were made.
    """
    retries = 0
    while True:
        response = await attempt(retries + 1)
        if response.status not in RETRYABLE or retries >= policy.max_retries:
            return response, retries + 1
        await sleep(retry_delay(response, retries, policy))
        retries += 1
