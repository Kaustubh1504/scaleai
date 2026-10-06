"""SQLite persistence for batches, documents and the audit trail (``storage_dir/intake.db``).

Every public method runs in its own short-lived connection and transaction
(``connect()``), so the store can be used from FastAPI's worker threads.
Timestamps are unix seconds from ``self.clock``.

Every status change and its audit event(s) are written in the same
``BEGIN IMMEDIATE`` transaction, after re-checking the status (and version)
under the write lock: two requests can never both win a transition, and the
audit trail can never disagree with the documents table. The audit table is
append-only (triggers reject UPDATE and DELETE) and its AUTOINCREMENT key is
never reused, so ``seq`` keeps increasing across restarts.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.classifier import Classification
from app.routing import AUTO_ACCEPTED, INGESTED, NEEDS_REVIEW, REVIEWED, Route
from mock_services.clock import Clock

SYSTEM = "system"

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
    classified_at REAL,
    -- routing and review
    status        TEXT NOT NULL DEFAULT 'ingested',  -- ingested | auto_accepted | needs_review | reviewed
    final_label   TEXT,
    review_reason TEXT,                              -- low_confidence | classification_failed | disagreement
    reviewed_by   TEXT,
    routed_at     REAL,
    version       INTEGER NOT NULL DEFAULT 1         -- +1 on every status change
);
CREATE INDEX IF NOT EXISTS documents_by_batch ON documents (batch_id, seq);
CREATE INDEX IF NOT EXISTS review_queue ON documents (status, routed_at, seq);

CREATE TABLE IF NOT EXISTS audit_events (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,   -- never reused, even after deletes or restarts
    ts          REAL NOT NULL,
    doc_id      TEXT NOT NULL,
    actor       TEXT NOT NULL,
    action      TEXT NOT NULL,
    from_status TEXT,
    to_status   TEXT NOT NULL,
    details     TEXT NOT NULL                        -- JSON object
);
CREATE INDEX IF NOT EXISTS audit_by_doc ON audit_events (doc_id, seq);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END;
"""


class DocumentNotFound(LookupError):
    pass


class StatusConflict(Exception):
    """The document is not in the state the request needs (HTTP 409)."""


class ReasonRequired(ValueError):
    """Overriding the model's label without a reason (HTTP 422)."""


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
                self._append(conn, doc["doc_id"], SYSTEM, "ingested", None, INGESTED, {"batch_id": batch_id})
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

    # -- documents --------------------------------------------------------

    def get_document(self, doc_id: str) -> dict | None:
        with self.connect() as conn:
            row = self._row(conn, doc_id)
            return self._view(row) if row else None

    def review_queue(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM documents WHERE status = ? ORDER BY routed_at, seq",
                                (NEEDS_REVIEW,)).fetchall()
            return [self._view(row) for row in rows]

    def record_classification(self, doc_id: str, result: Classification, route: Route) -> bool:
        """Store the classification and route the document, if it is still ``ingested``.

        Returns False (and changes nothing) when another run already routed it.
        """
        now = self.clock.time()
        with self.connect() as conn:
            row = self._row(conn, doc_id)
            if row is None or row["status"] != INGESTED:
                return False
            conn.execute(
                "UPDATE documents SET label = ?, confidence = ?, attempts = ?, error = ?, classified_at = ?, "
                "status = ?, final_label = ?, review_reason = ?, routed_at = ?, version = version + 1 "
                "WHERE doc_id = ?",
                (result.label, result.confidence, result.attempts, result.error, now,
                 route.status, route.final_label, route.review_reason, now, doc_id),
            )
            self._append(conn, doc_id, SYSTEM, "classified", INGESTED, INGESTED,
                         {"label": result.label, "confidence": result.confidence,
                          "attempts": result.attempts, "error": result.error})
            if route.status == AUTO_ACCEPTED:
                self._append(conn, doc_id, SYSTEM, "auto_accepted", INGESTED, AUTO_ACCEPTED,
                             {"final_label": route.final_label, "confidence": result.confidence})
            else:
                self._append(conn, doc_id, SYSTEM, "routed_to_review", INGESTED, NEEDS_REVIEW,
                             {"review_reason": route.review_reason})
            return True

    def review(self, doc_id: str, reviewer: str, label: str, reason: str | None,
               expected_version: int | None = None) -> dict:
        with self.connect() as conn:
            row = self._row(conn, doc_id)
            if row is None:
                raise DocumentNotFound(f"document {doc_id} not found")
            if row["status"] != NEEDS_REVIEW:
                raise StatusConflict(f"document {doc_id} is {row['status']}, not {NEEDS_REVIEW}")
            if expected_version is not None and expected_version != row["version"]:
                raise StatusConflict(f"document {doc_id} is at version {row['version']}, not {expected_version}")
            if row["label"] is not None and label != row["label"] and reason is None:
                raise ReasonRequired(f"label {label!r} overrides the model's {row['label']!r}; a reason is required")
            conn.execute("UPDATE documents SET status = ?, final_label = ?, reviewed_by = ?, version = version + 1 "
                         "WHERE doc_id = ?", (REVIEWED, label, reviewer, doc_id))
            self._append(conn, doc_id, reviewer, "reviewed", NEEDS_REVIEW, REVIEWED,
                         {"label": label, "model_label": row["label"], "reason": reason})
            return self._view(self._row(conn, doc_id))

    # -- audit ------------------------------------------------------------

    def audit_events(self, doc_id: str | None = None, actor: str | None = None, action: str | None = None,
                     since: float | None = None) -> list[dict]:
        filters = {"doc_id = ?": doc_id, "actor = ?": actor, "action = ?": action, "ts >= ?": since}
        # Clauses are constants; only the values come from the request, as bound parameters.
        used = {clause: value for clause, value in filters.items() if value is not None}
        where = " AND ".join(used) or "1 = 1"
        with self.connect() as conn:
            rows = conn.execute(f"SELECT * FROM audit_events WHERE {where} ORDER BY seq", tuple(used.values()))
            return [{**dict(row), "details": json.loads(row["details"])} for row in rows.fetchall()]

    def _append(self, conn: sqlite3.Connection, doc_id: str, actor: str, action: str, from_status: str | None,
                to_status: str, details: dict) -> None:
        conn.execute("INSERT INTO audit_events (ts, doc_id, actor, action, from_status, to_status, details) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (self.clock.time(), doc_id, actor, action, from_status, to_status, json.dumps(details)))

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _row(conn: sqlite3.Connection, doc_id: str) -> sqlite3.Row | None:
        return conn.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()

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
            "status": row["status"],
            "final_label": row["final_label"],
            "review_reason": row["review_reason"],
            "reviewed_by": row["reviewed_by"],
            "version": row["version"],
        }
