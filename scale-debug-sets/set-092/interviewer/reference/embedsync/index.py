from urllib.parse import quote, urlencode

from .transport import send


async def list_index(base_url, headers, collection, page_size):
    """Every entry the vector index currently holds for one collection."""
    items, token = [], None
    while True:
        query = {"limit": page_size}
        if token:
            query["page_token"] = token
        url = f"{base_url}/v1/index/{quote(collection)}?{urlencode(query)}"
        response = await send("GET", url, headers)
        if response.status != 200:
            raise RuntimeError(f"index listing for {collection} failed with HTTP {response.status}")
        page = response.body
        items.extend(page["items"])
        token = page.get("next_page_token")
        if not token:
            break
    return items
