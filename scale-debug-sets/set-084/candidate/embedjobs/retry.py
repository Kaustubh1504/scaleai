from .errors import ApiError, RateLimited, TransientError


async def create_with_retries(client, batch):
    attempts = client.config.max_attempts
    for attempt in range(attempts):
        try:
            return await client.create(batch)
        except TransientError:
            delay = client.config.backoff_s * 2 ** attempt
        except RateLimited as err:
            delay = err.retry_after_s if err.retry_after_s is not None else client.config.backoff_s * 2 ** attempt
        if attempt + 1 < attempts:
            await client.pause(batch.label, "retry", delay)
    raise ApiError("retries_exhausted")
