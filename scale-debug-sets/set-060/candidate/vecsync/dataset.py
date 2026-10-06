from datetime import datetime

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%SZ")


def parse_updated(text):
    text = (text or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


async def fetch_all(client):
    """Every record in the dataset, following next_page_token until it runs out."""
    records, token, pages = [], None, 0
    while True:
        page = await client.records_page(token)
        pages += 1
        token = page.get("next_page_token")
        if not token:
            break
        records.extend(page["records"])
    return records, pages


def select(records, since):
    """Records to embed: not deleted, non-blank text, updated on/after `since`."""
    chosen = []
    for rec in records:
        text = (rec.get("text") or "").strip()
        status = (rec.get("status") or "").strip().lower()
        updated = parse_updated(rec.get("updated"))
        if status == "deleted" or not text or updated is None or updated < since:
            continue
        chosen.append({"id": rec["id"].strip().lower(), "text": text})
    return chosen
