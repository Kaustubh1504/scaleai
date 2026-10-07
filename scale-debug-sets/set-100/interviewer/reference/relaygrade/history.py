from .wire import EvalError


async def fetch_baselines(client, page_size):
    """Read every record from the cursor-paginated baseline API (oldest run first)."""
    records, cursor = [], None
    while True:
        params = {"limit": page_size}
        if cursor:
            params["cursor"] = cursor
        status, page = await client.get_json("/v1/baselines", params)
        if status != 200:
            raise EvalError(f"baseline listing failed with HTTP {status}")
        records.extend(page["data"])
        cursor = page.get("next_cursor")
        if not cursor:
            return records


# VERIFIED
def latest_baselines(records):
    """prompt id -> score from its most recent run. Records arrive oldest first, so later ones win."""
    latest = {}
    for record in records:
        latest[record["prompt_id"].strip().lower()] = record["score"]
    return latest
