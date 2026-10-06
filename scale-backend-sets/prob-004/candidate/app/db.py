"""SQLite persistence for annotation tasks.

Every public method opens its own short-lived connection (``connect()``), so
the store is safe to use from FastAPI's worker threads. Timestamps are unix
seconds taken from ``self.clock``.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.models import NewTask
from mock_services.clock import Clock, RealClock

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    seq        INTEGER PRIMARY KEY AUTOINCREMENT,  -- creation order
    id         TEXT NOT NULL UNIQUE,
    data       TEXT NOT NULL,                       -- JSON object
    labels     TEXT NOT NULL,                       -- JSON array of allowed labels
    state      TEXT NOT NULL DEFAULT 'pending',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS tasks_by_state ON tasks (state, seq);

CREATE TABLE IF NOT EXISTS submissions (
    task_id      TEXT PRIMARY KEY REFERENCES tasks (id),
    annotator_id TEXT NOT NULL,
    label        TEXT NOT NULL,
    submitted_at REAL NOT NULL
);
"""


class TaskStore:
    def __init__(self, path: Path | str, clock: Clock | None = None):
        self.path = Path(path)
        self.clock = clock or RealClock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """A connection for one unit of work: commits on success, rolls back on error."""
        conn = sqlite3.connect(self.path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    # -- tasks ------------------------------------------------------------

    def create_tasks(self, entries: list[tuple[int, NewTask]]) -> tuple[list[str], list[dict]]:
        """Insert valid entries; returns (created ids, errors for duplicate ids)."""
        created: list[str] = []
        errors: list[dict] = []
        now = self.clock.time()
        with self.connect() as conn:
            for index, task in entries:
                task_id = task.id or uuid.uuid4().hex
                try:
                    conn.execute(
                        "INSERT INTO tasks (id, data, labels, created_at) VALUES (?, ?, ?, ?)",
                        (task_id, json.dumps(task.data), json.dumps(task.labels), now),
                    )
                except sqlite3.IntegrityError:
                    errors.append({"index": index, "error": f"id: task {task_id} already exists"})
                    continue
                created.append(task_id)
        return created, errors

    def get_task(self, task_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return self._view(conn, row) if row else None

    def list_tasks(self, state: str | None = None) -> list[dict]:
        with self.connect() as conn:
            if state is None:
                rows = conn.execute("SELECT * FROM tasks ORDER BY seq").fetchall()
            else:
                rows = conn.execute("SELECT * FROM tasks WHERE state = ? ORDER BY seq", (state,)).fetchall()
            return [self._view(conn, row) for row in rows]

    def oldest_pending(self) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE state = 'pending' ORDER BY seq LIMIT 1").fetchone()
            return self._view(conn, row) if row else None

    def set_state(self, task_id: str, state: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE tasks SET state = ? WHERE id = ?", (state, task_id))

    # -- submissions ------------------------------------------------------

    def record_submission(self, task_id: str, annotator_id: str, label: str) -> None:
        with self.connect() as conn:
            # Upsert: a client retrying the same request must not create a duplicate row.
            conn.execute(
                "INSERT OR REPLACE INTO submissions (task_id, annotator_id, label, submitted_at) "
                "VALUES (?, ?, ?, ?)",
                (task_id, annotator_id, label, self.clock.time()),
            )

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _view(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
        submissions = conn.execute(
            "SELECT annotator_id, label, submitted_at FROM submissions WHERE task_id = ? ORDER BY rowid",
            (row["id"],),
        ).fetchall()
        return {
            "id": row["id"],
            "data": json.loads(row["data"]),
            "labels": json.loads(row["labels"]),
            "state": row["state"],
            "created_at": row["created_at"],
            "submissions": [dict(s) for s in submissions],
        }
