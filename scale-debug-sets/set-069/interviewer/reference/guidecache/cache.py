import copy
from dataclasses import dataclass


@dataclass
class Entry:
    value: dict
    stored_at: float
    ttl_s: float

    @property
    def expires_at(self):
        return self.stored_at + self.ttl_s


class TTLCache:
    """In-memory TTL cache driven by an explicit clock (seconds since the epoch)."""

    def __init__(self):
        self._entries = {}

    def get(self, key, now):
        entry = self._entries.get(key)
        if entry is None:
            return None
        if now < entry.expires_at:
            return copy.deepcopy(entry.value)
        del self._entries[key]
        return None

    def put(self, key, value, now, ttl_s):
        self._entries[key] = Entry(copy.deepcopy(value), now, ttl_s)

    def __len__(self):
        return len(self._entries)
