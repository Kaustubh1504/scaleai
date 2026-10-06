from dataclasses import dataclass
from datetime import timedelta

from .store import CacheEntry, TTLCache


@dataclass
class ModelStats:
    hits: int = 0
    misses: int = 0
    last_refresh: object = None


class PrelabelBackend:
    """Stands in for the model server: every call returns a versioned pre-label id."""

    def __init__(self):
        self.versions = {}

    def version(self, model):
        return self.versions.get(model, 1)

    def publish(self, model):
        self.versions[model] = self.version(model) + 1

    def fetch(self, task_id, model, locale):
        return f"{model}@{self.version(model)}/{task_id}/{locale}"


def make_key(req):
    return (req.task_id, req.model)


def replay(requests, default_ttl, ttls):
    cache = TTLCache()
    backend = PrelabelBackend()
    stats = {}
    outcomes = []
    for req in requests:
        model_stats = stats.setdefault(req.model, ModelStats())
        if req.op == "publish":
            backend.publish(req.model)
            cache.drop_model(req.model)
            continue
        key = make_key(req)
        entry = cache.get(key, req.ts)
        if entry is not None:
            model_stats.hits += 1
            outcomes.append((req, "hit", entry.value))
            continue
        value = backend.fetch(req.task_id, req.model, req.locale)
        ttl = ttls.get(req.model, default_ttl)
        cache.put(key, CacheEntry(req.task_id, req.model, req.locale, value,
                                  stored_at=req.ts, expires_at=req.ts + timedelta(seconds=ttl)))
        model_stats.misses += 1
        model_stats.last_refresh = req.ts
        outcomes.append((req, "miss", value))
    return outcomes, stats, cache, backend
