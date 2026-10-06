import asyncio

from .models import CleanupError


async def list_index(transport, page_size):
    ids, cursor = [], None
    while True:
        params = {"limit": page_size}
        if cursor:
            params["cursor"] = cursor
        status, _, page = await transport.get("/v1/index", params)
        if status != 200:
            raise CleanupError(f"index listing failed with HTTP {status}")
        ids.extend(entry["id"] for entry in page["data"])
        if not page["has_more"]:
            break
        cursor = page["next_cursor"]
    return ids


async def delete_entry(transport, entry_id):
    status, _, _ = await transport.delete(f"/v1/index/{entry_id}")
    if status in (200, 204, 404):
        return True
    raise CleanupError(f"delete {entry_id} failed with HTTP {status}")


async def remove_stale(transport, stale):
    outcomes = await asyncio.gather(*(delete_entry(transport, i) for i in stale), return_exceptions=True)
    deleted = [i for i, out in zip(stale, outcomes) if not isinstance(out, BaseException)]
    failed = [i for i, out in zip(stale, outcomes) if isinstance(out, BaseException)]
    return deleted, failed
