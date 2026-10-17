# 25. SQLite that survives many threads (no "database is locked")
# Standalone: copy this file as-is. Deps: stdlib

import sqlite3
import threading
from contextlib import contextmanager

_local = threading.local()


def get_conn(path: str) -> sqlite3.Connection:
    """One connection per thread per file (connections must not be shared across threads).
    WAL lets readers run during writes; busy_timeout makes writers wait instead of failing."""
    conns = getattr(_local, "conns", None)
    if conns is None:
        conns = _local.conns = {}
    conn = conns.get(path)
    if conn is None:
        conn = sqlite3.connect(path, timeout=30, isolation_level=None)    # we control transactions
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conns[path] = conn
    return conn


@contextmanager
def write_tx(path: str):
    """BEGIN IMMEDIATE takes the write lock up front, so read-then-write logic (claim the oldest task,
    check-then-insert) is atomic across threads AND processes. Commits on success, rolls back on error."""
    conn = get_conn(path)
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
