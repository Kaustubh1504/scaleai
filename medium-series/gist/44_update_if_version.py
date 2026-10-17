# 44. Update only if nobody else did (optimistic concurrency)
# Standalone: copy this file as-is. Deps: stdlib

import sqlite3


def update_if_version(db_path: str, doc_id: str, expected_version: int, title: str) -> bool:
    """Compare-and-set in one statement. False -> someone changed it first (return 412)."""
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "UPDATE documents SET title = ?, version = version + 1 WHERE id = ? AND version = ?",
            (title, doc_id, expected_version))
        return cur.rowcount == 1
