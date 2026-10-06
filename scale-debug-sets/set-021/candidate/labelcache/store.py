from dataclasses import dataclass
from datetime import datetime


@dataclass
class CacheEntry:
    task_id: str
    model: str
    locale: str
    value: str
    stored_at: datetime
    expires_at: datetime


class TTLCache:
    def __init__(self):
        self._entries = {}

    def get(self, key, now):
        entry = self._entries.get(key)
        if entry is None:
            return None
        # fresh until the expiry instant
        if now <= entry.expires_at:
            return entry
        return None

    def put(self, key, entry):
        self._entries[key] = entry

    def drop_model(self, model):
        for key in [k for k, e in self._entries.items() if e.model == model]:
            del self._entries[key]

    # VERIFIED
    def purge_expired(self, now):
        for key in [k for k, e in self._entries.items() if e.expires_at <= now]:
            del self._entries[key]

    def entries(self):
        return list(self._entries.values())
