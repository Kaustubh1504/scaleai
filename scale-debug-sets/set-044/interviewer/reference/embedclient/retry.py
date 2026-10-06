import asyncio

from .transport import request

TRANSIENT = {429, 500, 502, 503, 504}


# VERIFIED
def backoff_delay(resp, attempt, base):
    retry_after = (resp.headers or {}).get("Retry-After")
    if retry_after is not None:
        return float(retry_after)
    return base * 2 ** attempt


async def post_with_retries(url, headers, payload, max_retries, backoff_seconds):
    attempt = 0
    while True:
        resp = await request("POST", url, headers, payload)
        if resp.status not in TRANSIENT or attempt >= max_retries:
            return resp
        await asyncio.sleep(backoff_delay(resp, attempt, backoff_seconds))
        attempt += 1
