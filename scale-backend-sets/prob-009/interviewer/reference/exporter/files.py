"""Crash-safe file writes: readers see the old file or the new one, never a partial one."""

from __future__ import annotations

import contextlib
import hashlib
import os
import tempfile
from pathlib import Path
from typing import BinaryIO, Iterator


@contextlib.contextmanager
def atomic_writer(path: Path) -> Iterator[BinaryIO]:
    """Write to ``.<name>.<random>.tmp`` in the same directory, then ``os.replace`` it over ``path``.

    On any exception (including KeyboardInterrupt) the temp file is removed and ``path`` is untouched.
    """
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            yield fh
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def write_atomic(path: Path, data: bytes) -> None:
    with atomic_writer(path) as fh:
        fh.write(data)


def sha256_file(path: Path) -> str | None:
    """Hex digest of the file's bytes, or None if it does not exist."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 16), b""):
                digest.update(chunk)
    except FileNotFoundError:
        return None
    return digest.hexdigest()
