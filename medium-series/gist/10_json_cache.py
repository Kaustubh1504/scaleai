# 10. Cache results across runs (checkpoint/resume, "re-run makes zero calls")
# Standalone: copy this file as-is. Deps: stdlib

import hashlib
import json
import os
import tempfile
from pathlib import Path


def cache_key(*parts) -> str:
    """Stable key from the inputs that affect the result: changed input -> new key -> recompute."""
    return hashlib.sha256(json.dumps(parts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load_cache(path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_cache(path, cache: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
