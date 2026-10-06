from collections import Counter


async def collect_usage(client):
    records, cursor = [], None
    while True:
        page = await client.usage_page(cursor)
        records.extend(page["data"])
        cursor = page.get("next_cursor")
        if cursor is None:
            break
    return records


def billed_tokens(records, models):
    totals = Counter()
    for record in records:
        totals[record["model"]] += record["tokens"]
    return {model: totals.get(model, 0) for model in models}
