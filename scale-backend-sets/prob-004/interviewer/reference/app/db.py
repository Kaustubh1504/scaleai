"""SQLite persistence for annotation tasks.

Every public method opens its own short-lived connection (``connect()``), so
the store is safe to use from FastAPI's worker threads. Timestamps are unix
seconds taken from ``self.clock``.

Concurrency: every method that changes state runs in one ``BEGIN IMMEDIATE``
transaction, which takes SQLite's write lock up front. Check-then-act
sequences (find a claimable task, then lease it) therefore cannot interleave
across threads or processes.

Leases: a lease is live while ``clock.time() < expires_at``. Expired rows are
ignored by every read and deleted lazily by ``claim``. The stored task state
is ``pending`` until the task is final; ``leased`` is derived from live leases,
so expiry needs no background job and survives restarts.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.consensus import decide
from app.models import NewTask
from mock_services.clock import Clock, RealClock

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    seq             INTEGER PRIMARY KEY AUTOINCREMENT,  -- creation order
    id              TEXT NOT NULL UNIQUE,
    data            TEXT NOT NULL,                       -- JSON object
    labels          TEXT NOT NULL,                       -- JSON array of allowed labels
    state           TEXT NOT NULL DEFAULT 'pending',     -- pending | submitted | completed | disputed
    created_at      REAL NOT NULL,
    gold_label      TEXT,
    consensus_label TEXT,
    agreement       REAL
);
CREATE INDEX IF NOT EXISTS tasks_by_state ON tasks (state, seq);

CREATE TABLE IF NOT EXISTS submissions (
    task_id      TEXT NOT NULL REFERENCES tasks (id),
    annotator_id TEXT NOT NULL,
    label        TEXT NOT NULL,
    submitted_at REAL NOT NULL,
    PRIMARY KEY (task_id, annotator_id)
);
CREATE INDEX IF NOT EXISTS submissions_by_annotator ON submissions (annotator_id);

CREATE TABLE IF NOT EXISTS leases (
    task_id      TEXT NOT NULL REFERENCES tasks (id),
    annotator_id TEXT NOT NULL,
    expires_at   REAL NOT NULL,
    PRIMARY KEY (task_id, annotator_id)
);
CREATE INDEX IF NOT EXISTS leases_by_annotator ON leases (annotator_id);
"""

FINAL_STATES = ("submitted", "completed", "disputed")

# Oldest task the annotator may lease. Run after expired leases are deleted,
# so every remaining lease row holds a slot.
CLAIMABLE_SQL = """
SELECT t.id FROM tasks t
WHERE t.state = 'pending'
  AND NOT EXISTS (SELECT 1 FROM submissions s WHERE s.task_id = t.id AND s.annotator_id = :annotator)
  AND (SELECT COUNT(*) FROM submissions s WHERE s.task_id = t.id)
    + (SELECT COUNT(*) FROM leases l WHERE l.task_id = t.id) < :redundancy
ORDER BY t.seq
LIMIT 1
"""


class TaskNotFound(LookupError):
    pass


class LeaseConflict(Exception):
    pass


class LabelNotAllowed(ValueError):
    pass


class TaskStore:
    def __init__(self, path: Path | str, clock: Clock | None = None, lease_seconds: float = 60,
                 redundancy: int = 1):
        self.path = Path(path)
        self.clock = clock or RealClock()
        self.lease_seconds = lease_seconds
        self.redundancy = redundancy
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=10.0)
        try:
            # WAL lets readers proceed while a claim holds the write lock.
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA)
        finally:
            conn.close()

    @contextmanager
    def connect(self, write: bool = False) -> Iterator[sqlite3.Connection]:
        """One transaction: commits on success, rolls back on error.

        ``write=True`` takes the write lock immediately (``BEGIN IMMEDIATE``);
        other writers wait up to ``timeout`` seconds instead of failing.
        """
        conn = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield conn
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    # -- tasks ------------------------------------------------------------

    def create_tasks(self, entries: list[tuple[int, NewTask]]) -> tuple[list[str], list[dict]]:
        """Insert valid entries; returns (created ids, errors for duplicate ids)."""
        created: list[str] = []
        errors: list[dict] = []
        now = self.clock.time()
        with self.connect(write=True) as conn:
            for index, task in entries:
                task_id = task.id or uuid.uuid4().hex
                try:
                    conn.execute(
                        "INSERT INTO tasks (id, data, labels, created_at, gold_label) VALUES (?, ?, ?, ?, ?)",
                        (task_id, json.dumps(task.data), json.dumps(task.labels), now, task.gold_label),
                    )
                except sqlite3.IntegrityError:
                    errors.append({"index": index, "error": f"id: task {task_id} already exists"})
                    continue
                created.append(task_id)
        return created, errors

    def get_task(self, task_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return self._view(conn, row, self.clock.time()) if row else None

    def list_tasks(self, state: str | None = None) -> list[dict]:
        now = self.clock.time()
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY seq").fetchall()
            views = [self._view(conn, row, now) for row in rows]
        return [v for v in views if state is None or v["state"] == state]

    # -- leases -----------------------------------------------------------

    def claim(self, annotator_id: str) -> dict | None:
        """The caller's live lease, else a new lease on the oldest claimable task, else None."""
        now = self.clock.time()
        with self.connect(write=True) as conn:
            conn.execute("DELETE FROM leases WHERE expires_at <= ?", (now,))
            held = conn.execute(
                "SELECT task_id, expires_at FROM leases WHERE annotator_id = ?", (annotator_id,)
            ).fetchone()
            if held is not None:
                task_id, expires_at = held["task_id"], held["expires_at"]
            else:
                row = conn.execute(CLAIMABLE_SQL, {"annotator": annotator_id,
                                                   "redundancy": self.redundancy}).fetchone()
                if row is None:
                    return None
                task_id, expires_at = row["id"], now + self.lease_seconds
                conn.execute("INSERT INTO leases (task_id, annotator_id, expires_at) VALUES (?, ?, ?)",
                             (task_id, annotator_id, expires_at))
            return {**self._view(conn, self._task_row(conn, task_id), now), "lease_expires_at": expires_at}

    def extend(self, task_id: str, annotator_id: str) -> dict:
        now = self.clock.time()
        with self.connect(write=True) as conn:
            row = self._task_row(conn, task_id)
            self._require_live_lease(conn, row, annotator_id, now)
            expires_at = now + self.lease_seconds
            conn.execute("UPDATE leases SET expires_at = ? WHERE task_id = ? AND annotator_id = ?",
                         (expires_at, task_id, annotator_id))
            return {**self._view(conn, row, now), "lease_expires_at": expires_at}

    def submit(self, task_id: str, annotator_id: str, label: str) -> dict:
        now = self.clock.time()
        with self.connect(write=True) as conn:
            row = self._task_row(conn, task_id)
            self._require_live_lease(conn, row, annotator_id, now)
            labels = json.loads(row["labels"])
            if label not in labels:
                raise LabelNotAllowed(f"label {label!r} is not one of {labels}")
            conn.execute("DELETE FROM leases WHERE task_id = ? AND annotator_id = ?", (task_id, annotator_id))
            conn.execute(
                "INSERT INTO submissions (task_id, annotator_id, label, submitted_at) VALUES (?, ?, ?, ?)",
                (task_id, annotator_id, label, now),
            )
            votes = [r["label"] for r in conn.execute(
                "SELECT label FROM submissions WHERE task_id = ? ORDER BY rowid", (task_id,))]
            if len(votes) >= self.redundancy:
                outcome = decide(votes, self.redundancy)
                conn.execute("UPDATE tasks SET state = ?, consensus_label = ?, agreement = ? WHERE id = ?",
                             (*outcome, task_id))
            return self._view(conn, self._task_row(conn, task_id), now)

    # -- quality ----------------------------------------------------------

    def annotator_stats(self, annotator_id: str) -> dict:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS seen, COALESCE(SUM(s.label = t.gold_label), 0) AS correct "
                "FROM submissions s JOIN tasks t ON t.id = s.task_id "
                "WHERE s.annotator_id = ? AND t.gold_label IS NOT NULL",
                (annotator_id,),
            ).fetchone()
        seen, correct = row["seen"], row["correct"]
        return {"annotator_id": annotator_id, "gold_seen": seen, "gold_correct": correct,
                "accuracy": round(correct / seen, 2) if seen else None}

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _task_row(conn: sqlite3.Connection, task_id: str) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise TaskNotFound(f"task {task_id} not found")
        return row

    @staticmethod
    def _require_live_lease(conn: sqlite3.Connection, row: sqlite3.Row, annotator_id: str, now: float) -> None:
        if row["state"] in FINAL_STATES:
            raise LeaseConflict(f"task {row['id']} is already {row['state']}")
        lease = conn.execute(
            "SELECT 1 FROM leases WHERE task_id = ? AND annotator_id = ? AND expires_at > ?",
            (row["id"], annotator_id, now),
        ).fetchone()
        if lease is None:
            raise LeaseConflict(f"annotator {annotator_id} does not hold a live lease on task {row['id']}")

    @staticmethod
    def _view(conn: sqlite3.Connection, row: sqlite3.Row, now: float) -> dict:
        leases = conn.execute(
            "SELECT annotator_id, expires_at FROM leases WHERE task_id = ? AND expires_at > ? "
            "ORDER BY expires_at, annotator_id",
            (row["id"], now),
        ).fetchall()
        submissions = conn.execute(
            "SELECT annotator_id, label, submitted_at FROM submissions WHERE task_id = ? ORDER BY rowid",
            (row["id"],),
        ).fetchall()
        state = row["state"]
        if state == "pending" and leases:
            state = "leased"
        return {
            "id": row["id"],
            "data": json.loads(row["data"]),
            "labels": json.loads(row["labels"]),
            "state": state,
            "created_at": row["created_at"],
            "consensus_label": row["consensus_label"],
            "agreement": row["agreement"],
            "leases": [dict(lease) for lease in leases],
            "submissions": [dict(s) for s in submissions],
        }
