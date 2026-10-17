# 07. Write a file atomically
# Standalone: copy this file as-is. Deps: stdlib

import json
import os
import tempfile
from pathlib import Path


def atomic_write_json(path: Path, data) -> None:
    """Readers see the old file or the new one, never half. No temp file left behind on failure."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2)          # fail before touching disk
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
