from dataclasses import dataclass
from datetime import datetime


@dataclass
class Entry:
    value: dict
    stored_at: datetime


class TTLCache:
    def __init__(self, ttls):
        self.ttls = ttls
        self._entries = {}

    def ttl_for(self, key):
        return self.ttls.get(key[0], self.ttls["default"])

    # VERIFIED
    def get(self, key, now):
        entry = self._entries.get(key)
        if entry is None:
            return None
        age = (now - entry.stored_at).total_seconds()
        if age < self.ttl_for(key):
            return dict(entry.value)
        del self._entries[key]
        return None

    def put(self, key, value, now):
        self._entries[key] = Entry(value, now)

    def invalidate_sku(self, sku):
        for key in [k for k in self._entries if k[1] == sku]:
            del self._entries[key]
