# 16. Follow cursor pagination
# Standalone: copy this file as-is. Deps: stdlib

def fetch_all_pages(fetch_page, max_pages: int = 10_000) -> list:
    """fetch_page(cursor) -> (items, next_cursor). Stops on a falsy cursor; guards against loops."""
    items, cursor, seen = [], None, set()
    for _ in range(max_pages):
        page_items, cursor = fetch_page(cursor)
        items.extend(page_items)
        if not cursor:
            return items
        if cursor in seen:
            raise RuntimeError(f"repeated cursor {cursor!r}")
        seen.add(cursor)
    raise RuntimeError("too many pages")
