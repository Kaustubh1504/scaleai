"""Durable task and idempotency storage in sqlite.

A task and its idempotency record are written in one transaction, so a crash
can never leave a task without its record (or a record without its task).
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    seq       INTEGER PRIMARY KEY AUTOINCREMENT,
    id        TEXT NOT NULL UNIQUE,
    tenant_id TEXT NOT NULL,
    doc       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS tasks_by_tenant ON tasks (tenant_id, seq);
CREATE TABLE IF NOT EXISTS idempotency (
    tenant_id   TEXT NOT NULL,
    key         TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    status      INTEGER NOT NULL,
    response    TEXT NOT NULL,
    created_at  REAL NOT NULL,
    PRIMARY KEY (tenant_id, key)
);
"""


@dataclass(frozen=True)
class IdempotencyRecord:
    fingerprint: str
    status: int
    response: dict
    created_at: float


class KeyTaken(Exception):
    """Another writer (thread or process) recorded this idempotency key first."""


class Store:
    def __init__(self, root: Path):
        self._path = root / "intake.sqlite3"
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    def _db(self) -> sqlite3.Connection:
        # Opened lazily so importing the module (app = create_app()) touches no disk.
        if self._conn is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._path, check_same_thread=False)
            conn.executescript(_SCHEMA)
            self._conn = conn
        return self._conn

    def get_task(self, tenant_id: str, task_id: str) -> dict | None:
        with self._lock:
            row = self._db().execute("SELECT doc FROM tasks WHERE id = ? AND tenant_id = ?",
                                     (task_id, tenant_id)).fetchone()
        return json.loads(row[0]) if row else None

    def list_tasks(self, tenant_id: str) -> list[dict]:
        with self._lock:
            rows = self._db().execute("SELECT doc FROM tasks WHERE tenant_id = ? ORDER BY seq",
                                      (tenant_id,)).fetchall()
        return [json.loads(doc) for (doc,) in rows]

    def get_record(self, tenant_id: str, key: str) -> IdempotencyRecord | None:
        with self._lock:
            row = self._db().execute(
                "SELECT fingerprint, status, response, created_at FROM idempotency WHERE tenant_id = ? AND key = ?",
                (tenant_id, key)).fetchone()
        return IdempotencyRecord(row[0], row[1], json.loads(row[2]), row[3]) if row else None

    def create_task(self, task: dict, key: str | None, fingerprint: str, now: float, expired_before: float) -> None:
        """Insert the task and (if keyed) its idempotency record in one transaction.

        An expired record for the key is replaced; a live one raises KeyTaken and
        nothing is written, so the (tenant, key) primary key is what guarantees one
        task per key even across processes sharing the database.
        """
        with self._lock, self._db() as conn:
            if key is not None:
                conn.execute("DELETE FROM idempotency WHERE tenant_id = ? AND key = ? AND created_at <= ?",
                             (task["tenant_id"], key, expired_before))
                try:
                    conn.execute("INSERT INTO idempotency VALUES (?, ?, ?, ?, ?, ?)",
                                 (task["tenant_id"], key, fingerprint, 201, json.dumps(task), now))
                except sqlite3.IntegrityError as exc:
                    raise KeyTaken(key) from exc
            conn.execute("INSERT INTO tasks (id, tenant_id, doc) VALUES (?, ?, ?)",
                         (task["id"], task["tenant_id"], json.dumps(task)))
