async def collect_index(client, collection):
    """Every vector id stored for `collection`, following the offset pages."""
    ids, offset = [], 0
    while True:
        page = await client.vector_page(collection, offset)
        items = page.get("items") or []
        ids.extend(item["id"] for item in items)
        offset += client.config.page_size
        if not items or not page.get("has_more"):
            break
    return ids


def coverage(index, results, ok_status):
    """collection -> stored count and the accepted documents the index does not list."""
    report = {}
    for collection, ids in index.items():
        accepted = {d for r in results if r.collection == collection and r.status is ok_status for d in r.doc_ids}
        report[collection] = {"stored": len(ids), "missing": sorted(accepted - set(ids))}
    return report
