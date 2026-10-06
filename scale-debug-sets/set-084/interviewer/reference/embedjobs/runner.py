import asyncio

from .retry import create_with_retries


async def run_batches(client, batches):
    sem = asyncio.Semaphore(client.config.max_concurrency)

    async def run_one(batch):
        async with sem:
            batch_id = await create_with_retries(client, batch)
            await client.wait_until_done(batch.label, batch_id)
            items = await client.results(batch_id)
        return {item["id"]: item["embedding"] for item in items}

    outcomes = await asyncio.gather(*(run_one(b) for b in batches), return_exceptions=True)
    embedded, failures = {}, {}
    for batch, outcome in zip(batches, outcomes):
        if isinstance(outcome, Exception):
            failures[batch.label] = getattr(outcome, "reason", type(outcome).__name__)
        else:
            embedded.update(outcome)
    return embedded, failures
