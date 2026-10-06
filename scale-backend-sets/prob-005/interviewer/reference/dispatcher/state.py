"""Durable delivery state and the audit log, both under the dispatcher's state_dir."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Iterable

DeliveryKey = tuple[str, str]  # (event_id, subscription_id)


class StateError(RuntimeError):
    """The saved state cannot be read. Refuse to start rather than re-send everything."""


def write_json_atomic(path: Path, data: object) -> None:
    """Write to a temp file in the same directory, fsync, then rename over the target."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class DeliveryStore:
    """All delivery records in one JSON file, rewritten atomically on every save."""

    VERSION = 1

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[DeliveryKey, dict]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if raw.get("version") != self.VERSION:
                raise ValueError(f"unsupported state version {raw.get('version')!r}")
            return {(d["event_id"], d["subscription_id"]): d for d in raw["deliveries"]}
        except FileNotFoundError:
            return {}
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise StateError(f"cannot load delivery state from {self.path}: {exc}") from exc

    def save(self, deliveries: Iterable[dict]) -> None:
        write_json_atomic(self.path, {"version": self.VERSION, "deliveries": list(deliveries)})


class AuditLog:
    """Append-only JSON Lines record of every delivery attempt."""

    def __init__(self, path: Path):
        self.path = path

    def append(self, entry: dict) -> None:
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
