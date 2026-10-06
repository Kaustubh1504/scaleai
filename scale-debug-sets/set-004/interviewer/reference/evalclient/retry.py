import time
from dataclasses import dataclass

RETRYABLE = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int
    backoff_seconds: float


def wait_time(response, policy, attempt):
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        return float(retry_after)
    return policy.backoff_seconds * (2 ** attempt)


def send_with_retries(do_request, policy, sleep=time.sleep):
    response = None
    for attempt in range(policy.max_retries + 1):
        response = do_request()
        if response.status not in RETRYABLE:
            return response
        if attempt < policy.max_retries:
            sleep(wait_time(response, policy, attempt))
    return response
