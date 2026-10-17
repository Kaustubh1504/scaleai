# 49. Fake HTTP server: scripted replies, call counting, max concurrency
# Standalone: copy this file as-is. Deps: stdlib

from collections import Counter, defaultdict


def group_by(items, key):
    out = defaultdict(list)
    for it in items:
        out[key(it)].append(it)
    return dict(out)


def top_counts(items, key, n: int = 1):
    """Most common first; ties broken by the key ascending (deterministic)."""
    return sorted(Counter(key(it) for it in items).items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def dedupe(items, key):
    """Keep the first occurrence of each key, preserve order."""
    seen, out = set(), []
    for it in items:
        k = key(it)
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


def latest_by(items, key, version, deleted=lambda it: False):
    """Highest version wins regardless of arrival order; tombstones removed at the end."""
    best = {}
    for it in items:
        k = key(it)
        if k not in best or version(it) > version(best[k]):
            best[k] = it
    return [it for it in best.values() if not deleted(it)]
