from urllib.parse import urlencode

from .transport import request


async def list_index_ids(base_url, headers, page_size):
    """Every doc id currently stored in the remote index, following the cursor."""
    ids, cursor = [], None
    while True:
        query = {"limit": page_size}
        if cursor:
            query["cursor"] = cursor
        resp = await request("GET", f"{base_url.rstrip('/')}/v1/index?{urlencode(query)}", headers)
        if resp.status != 200:
            raise RuntimeError(f"index listing failed: HTTP {resp.status}")
        ids.extend(resp.body["ids"])
        cursor = resp.body.get("next_cursor")
        if not cursor:
            break
    return ids
