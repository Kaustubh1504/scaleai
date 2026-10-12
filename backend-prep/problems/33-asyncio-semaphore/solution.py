"""33. asyncio fan-out with a semaphore: reference solution."""

import asyncio

import httpx


class ApiError(Exception):
    def __init__(self, status: int, response_id: str, message: str = ""):
        super().__init__(f"{status} for {response_id}: {message}")
        self.status = status
        self.response_id = response_id


async def fetch_all(client: httpx.AsyncClient, ids: list[str], limit: int = 5) -> list[dict]:
    if limit < 1:
        raise ValueError("limit must be >= 1")
    sem = asyncio.Semaphore(limit)

    async def fetch(rid: str) -> dict:
        async with sem:
            resp = await client.get(f"/v1/responses/{rid}")
        if not resp.is_success:
            raise ApiError(resp.status_code, rid, resp.text)
        return resp.json()

    return list(await asyncio.gather(*(fetch(rid) for rid in ids)))


if __name__ == "__main__":
    from problem_api import make_api, response_id

    async def main() -> None:
        api = make_api(n_responses=100, latency_s=0.02)
        async with api.async_client() as client:
            rows = await fetch_all(client, [response_id(i) for i in range(1, 101)], limit=10)
        print(len(rows), "responses, max in flight =", api.max_in_flight)

    asyncio.run(main())
