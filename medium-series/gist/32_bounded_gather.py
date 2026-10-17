# 32. Same thing in async code
# Standalone: copy this file as-is. Deps: stdlib

import asyncio


async def bounded_gather(fn, items, limit: int = 5) -> list:
    """await fn(item) for every item, at most `limit` at once, results in input order."""
    sem = asyncio.Semaphore(limit)

    async def run(item):
        async with sem:
            return await fn(item)

    return await asyncio.gather(*(run(i) for i in items))
