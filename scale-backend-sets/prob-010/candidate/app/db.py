"""SQLite persistence for batches and documents (``storage_dir/intake.db``).

Every public method runs in its own short-lived connection and transaction
(``connect()``), so the store can be used from FastAPI's worker threads.
Timestamps are unix seconds from ``self.clock``.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.classifier import Classification
from mock_services.clock import Clock

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    batch_id   TEXT PRIMARY KEY,
    filename   TEXT NOT NULL,
    total_rows INTEGER NOT NULL,
    errors     TEXT NOT NULL,                       -- JSON array of {"row", "error"}
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    seq           INTEGER PRIMARY KEY AUTOINCREMENT, -- upload order
    doc_id        TEXT NOT NULL UNIQUE,              -- unique across all batches
    batch_id      TEXT NOT NULL REFERENCES batches (batch_id),
    title         TEXT NOT NULL,
    text          TEXT NOT NULL,
    created_at    REAL NOT NULL,
    -- latest classification; all NULL until the batch is classified
    label         TEXT,
    confidence    REAL,
    attempts      INTEGER,
    error         TEXT,
    classified_at REAL
);
CREATE INDEX IF NOT EXISTS documents_by_batch ON documents (batch_id, seq);
"""


class DocumentStore:
    def __init__(self, path: Path | str, clock: Clock):
        self.path = Path(path)
        self.clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=10.0)
        try:
            conn.executescript(SCHEMA)
        finally:
            conn.close()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """One transaction: commits on success, rolls back on error.

        ``BEGIN IMMEDIATE`` takes the write lock up front; other connections wait
        up to ``timeout`` seconds for it instead of failing with "database is locked".
        """
        conn = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    # -- batches ----------------------------------------------------------

    def create_batch(self, filename: str, total_rows: int, documents: list[tuple[int, dict]],
                     errors: list[dict]) -> dict:
        """Store a batch and its valid documents. A doc_id that already exists is a row error."""
        batch_id = uuid.uuid4().hex
        now = self.clock.time()
        accepted: list[str] = []
        errors = list(errors)
        with self.connect() as conn:
            conn.execute("INSERT INTO batches (batch_id, filename, total_rows, errors, created_at) "
                         "VALUES (?, ?, ?, '[]', ?)", (batch_id, filename, total_rows, now))
            for row, doc in documents:
                try:
                    conn.execute("INSERT INTO documents (doc_id, batch_id, title, text, created_at) "
                                 "VALUES (?, ?, ?, ?, ?)", (doc["doc_id"], batch_id, doc["title"], doc["text"], now))
                except sqlite3.IntegrityError:
                    errors.append({"row": row, "error": f"doc_id {doc['doc_id']!r} already exists"})
                    continue
                accepted.append(doc["doc_id"])
            errors.sort(key=lambda e: e["row"])
            conn.execute("UPDATE batches SET errors = ? WHERE batch_id = ?", (json.dumps(errors), batch_id))
        return {"batch_id": batch_id, "filename": filename, "total_rows": total_rows,
                "accepted": accepted, "errors": errors}

    def get_batch(self, batch_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM batches WHERE batch_id = ?", (batch_id,)).fetchone()
            if row is None:
                return None
            return {
                "batch_id": row["batch_id"],
                "filename": row["filename"],
                "total_rows": row["total_rows"],
                "errors": json.loads(row["errors"]),
                "created_at": row["created_at"],
                "documents": self._batch_documents(conn, batch_id),
            }

    def batch_documents(self, batch_id: str) -> list[dict]:
        with self.connect() as conn:
            return self._batch_documents(conn, batch_id)

    # -- classification ---------------------------------------------------

    def save_classification(self, doc_id: str, result: Classification) -> None:
        """Overwrite the document's classification with ``result``."""
        with self.connect() as conn:
            conn.execute(
                "UPDATE documents SET label = ?, confidence = ?, attempts = ?, error = ?, classified_at = ? "
                "WHERE doc_id = ?",
                (result.label, result.confidence, result.attempts, result.error, self.clock.time(), doc_id),
            )

    # -- helpers ----------------------------------------------------------

    def _batch_documents(self, conn: sqlite3.Connection, batch_id: str) -> list[dict]:
        rows = conn.execute("SELECT * FROM documents WHERE batch_id = ? ORDER BY seq", (batch_id,)).fetchall()
        return [self._view(row) for row in rows]

    @staticmethod
    def _view(row: sqlite3.Row) -> dict:
        classification = None
        if row["classified_at"] is not None:
            classification = {
                "label": row["label"],
                "confidence": row["confidence"],
                "attempts": row["attempts"],
                "error": row["error"],
                "classified_at": row["classified_at"],
            }
        return {
            "doc_id": row["doc_id"],
            "batch_id": row["batch_id"],
            "title": row["title"],
            "text": row["text"],
            "created_at": row["created_at"],
            "classification": classification,
        }
