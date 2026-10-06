"""JSON documents on local disk, written atomically."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

# Upload ids are uuid4 hex; anything else could escape the storage directory.
_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def valid_id(upload_id: str) -> bool:
    return bool(_ID_RE.match(upload_id))


def write_json_atomic(path: Path, data: dict) -> None:
    """Write to a temp file in the same directory, then rename over the target."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


class Store:
    def __init__(self, root: Path):
        self.root = root

    def _upload_path(self, upload_id: str) -> Path:
        return self.root / "uploads" / f"{upload_id}.json"

    def _classification_path(self, upload_id: str) -> Path:
        return self.root / "classifications" / f"{upload_id}.json"

    def save_upload(self, doc: dict) -> None:
        write_json_atomic(self._upload_path(doc["upload_id"]), doc)

    def load_upload(self, upload_id: str) -> dict | None:
        return read_json(self._upload_path(upload_id)) if valid_id(upload_id) else None

    def save_classifications(self, doc: dict) -> None:
        write_json_atomic(self._classification_path(doc["upload_id"]), doc)

    def load_classifications(self, upload_id: str) -> dict | None:
        return read_json(self._classification_path(upload_id)) if valid_id(upload_id) else None
