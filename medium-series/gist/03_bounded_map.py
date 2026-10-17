# 03. Run a function over many items, N at a time, keeping order (threads)
# Standalone: copy this file as-is. Deps: stdlib

from concurrent.futures import ThreadPoolExecutor


def bounded_map(fn, items, max_workers: int = 5) -> list:
    """fn(item) for every item, at most max_workers at once, results in input order."""
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(fn, items))
