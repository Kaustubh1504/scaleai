# 34. Store an event exactly once (idempotent receiver)
# Standalone: copy this file as-is. Deps: stdlib

import sqlite3


def insert_once(db_path: str, event_id: str, payload: str) -> bool:
    """True if this event is new, False if it was already stored. Atomic even under concurrent retries."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, payload TEXT, "
                     "status TEXT DEFAULT 'pending')")
        cur = conn.execute("INSERT OR IGNORE INTO events (id, payload) VALUES (?, ?)", (event_id, payload))
        return cur.rowcount == 1
