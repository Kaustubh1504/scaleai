import asyncio

from .retry import RetryPolicy, with_retries
from .stream import assemble
from .wire import EvalError


class Runner:
    def __init__(self, client, config, sleep=asyncio.sleep):
        self.client = client
        self.sleep = sleep
        self.policy = RetryPolicy(config.max_retries, config.backoff_seconds)
        self.limit = asyncio.Semaphore(config.max_concurrency)
        self.attempts = {}
        self.blocked = []

    async def run_one(self, prompt):
        if prompt.review and self.client.policy_blocks(prompt.id):
            self.blocked.append(prompt.id)
            return None
        async with self.limit:
            response, attempts = await with_retries(
                lambda n: self.client.complete(prompt, n), self.policy, self.sleep)
        self.attempts[prompt.id] = attempts
        if response.status != 200:
            raise EvalError(f"HTTP {response.status}")
        return assemble(response.body)

    async def run_all(self, prompts):
        outcomes = await asyncio.gather(*(self.run_one(p) for p in prompts), return_exceptions=True)
        completions, failed = {}, {}
        for prompt, outcome in zip(prompts, outcomes):
            if isinstance(outcome, Exception):
                continue
            if outcome is not None:
                completions[prompt.id] = outcome
        return completions, failed
