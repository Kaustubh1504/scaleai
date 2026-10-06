from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Entry:
    value: dict
    expires_at: datetime


class TTLCache:
    def __init__(self):
        self._entries = {}

    def get(self, key, now):
        entry = self._entries.get(key)
        if entry is None:
            return None
        if now <= entry.expires_at:
            return dict(entry.value)
        del self._entries[key]
        return None

    def put(self, key, value, now, ttl_seconds):
        self._entries[key] = Entry(dict(value), now + timedelta(seconds=ttl_seconds))

    def __len__(self):
        return len(self._entries)
