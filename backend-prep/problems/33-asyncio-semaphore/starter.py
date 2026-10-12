"""33. asyncio fan-out with a semaphore

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import asyncio
import httpx


class ApiError(Exception):
    def __init__(self, status: int, response_id: str, message: str = ""):
        super().__init__(f"{status} for {response_id}: {message}")
        self.status = status
        self.response_id = response_id


async def fetch_all(client: httpx.AsyncClient, ids: list[str], limit: int = 5) -> list[dict]:
    raise NotImplementedError


if __name__ == "__main__":
    import time

    from problem_api import make_api, response_id

    async def main() -> None:
        api = make_api(n_responses=100, latency_s=0.02)
        ids = [response_id(i) for i in range(1, 101)]
        started = time.perf_counter()
        async with api.async_client() as client:
            rows = await fetch_all(client, ids, limit=10)
        print(f"{len(rows)} responses in {time.perf_counter() - started:.2f}s, max in flight = {api.max_in_flight}")
        print(rows[0])

    asyncio.run(main())
