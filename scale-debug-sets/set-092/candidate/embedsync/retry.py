import asyncio
from dataclasses import dataclass

TRANSIENT = {429, 500, 502, 503, 504}


@dataclass
class RetryPolicy:
    max_retries: int
    backoff_seconds: float

    def delay(self, attempt, response):
        header = response.headers.get("Retry-After")
        if header is not None:
            return float(header)
        return self.backoff_seconds * 2 ** attempt


async def with_retries(call, policy, sleep=asyncio.sleep):
    attempt = 0
    while True:
        response = await call()
        if response.status not in TRANSIENT or attempt >= policy.max_retries:
            return response
        sleep(policy.delay(attempt, response))
        attempt += 1
