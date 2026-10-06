import asyncio
from dataclasses import dataclass, field


@dataclass
class ShardOutcome:
    shard: str
    status: str
    tokens: int = 0
    results: dict = field(default_factory=dict)


def classify(item, threshold):
    score = float(item["score"])
    status = "labeled" if score >= threshold else "needs_review"
    return {"status": status, "label": item["label"], "score": score}


async def process_shard(client, shard, items):
    batch_id = await client.submit(shard, items)
    batch = await client.poll_until_done(batch_id)
    outcome = ShardOutcome(shard, batch["status"])
    if batch["status"] == "completed":
        outcome.tokens = batch.get("usage", {}).get("total_tokens", 0)
        for item in await client.fetch_results(batch_id):
            outcome.results[item["id"]] = classify(item, client.config.review_threshold)
    await client.archive(batch_id)
    return outcome


async def run_shard(limit, client, shard, items):
    async with limit:
        return await process_shard(client, shard, items)


async def run_all(client, shards):
    limit = asyncio.Semaphore(client.config.max_concurrency)
    tasks = [run_shard(limit, client, shard, items) for shard, items in shards.items()]
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        shard: outcome if not isinstance(outcome, BaseException) else ShardOutcome(shard, "error")
        for shard, outcome in zip(shards, outcomes)
    }
