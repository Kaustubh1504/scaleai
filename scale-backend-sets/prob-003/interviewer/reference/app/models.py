"""Request validation and the canonical form used to compare request bodies."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

IDEMPOTENCY_KEY_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def valid_idempotency_key(key: str) -> bool:
    return IDEMPOTENCY_KEY_RE.fullmatch(key) is not None


class TaskIn(BaseModel):
    # strict: "3", 3.0 and true are not priorities; extra fields are rejected.
    model_config = ConfigDict(extra="forbid", strict=True)

    project: str = Field(min_length=1)
    payload: dict[str, Any]
    priority: int = Field(default=5, ge=0, le=9)

    def fingerprint(self) -> str:
        """Canonical JSON of the validated request: key order, whitespace and defaults don't matter."""
        return json.dumps(self.model_dump(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
