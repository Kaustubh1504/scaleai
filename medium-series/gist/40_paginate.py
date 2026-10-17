# 40. Paginate your own endpoint (keyset cursor)
# Standalone: copy this file as-is. Deps: stdlib

import base64
import json


def encode_cursor(value) -> str:
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode()


def decode_cursor(cursor: str):
    """ValueError on garbage (map to 400)."""
    try:
        value = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    except Exception:
        raise ValueError("invalid cursor") from None
    return tuple(value) if isinstance(value, list) else value


def paginate(items, limit: int = 20, cursor=None, key=lambda it: it["id"], max_limit: int = 100) -> dict:
    """Sort by key, return up to `limit` items after the cursor + next_cursor (None on the last page).
    Keyset, not offset: rows added between requests don't shift pages. Filter items before calling."""
    limit = max(1, min(int(limit), max_limit))
    ordered = sorted(items, key=key)
    if cursor:
        after = decode_cursor(cursor)
        ordered = [it for it in ordered if key(it) > after]
    page = ordered[:limit]
    next_cursor = encode_cursor(key(page[-1])) if len(ordered) > limit else None
    return {"data": page, "next_cursor": next_cursor}
