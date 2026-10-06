"""Customer webhook subscriptions, loaded from a JSON file.

    [{"id": "sub_acme", "url": "https://acme.example/hooks", "secret": "whsec_...",
      "event_types": ["task.completed", "batch.exported"]}]

``event_types`` may contain ``"*"`` to receive every event type.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
WILDCARD = "*"


class SubscriptionError(ValueError):
    """The subscriptions file is unusable. The message says which entry and why."""


@dataclass(frozen=True)
class Subscription:
    id: str
    url: str
    secret: str
    event_types: tuple[str, ...]

    def wants(self, event_type: str) -> bool:
        return WILDCARD in self.event_types or event_type in self.event_types


def _parse_one(index: int, raw: Any) -> Subscription:
    where = f"subscription #{index + 1}"
    if not isinstance(raw, dict):
        raise SubscriptionError(f"{where}: must be a JSON object")
    sub_id, url, secret, types = raw.get("id"), raw.get("url"), raw.get("secret"), raw.get("event_types")
    if not isinstance(sub_id, str) or not ID_RE.match(sub_id):
        raise SubscriptionError(f"{where}: 'id' must match {ID_RE.pattern}")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise SubscriptionError(f"{sub_id}: 'url' must be an http(s) URL")
    if not isinstance(secret, str) or not secret:
        raise SubscriptionError(f"{sub_id}: 'secret' must be a non-empty string")
    if not isinstance(types, list) or not types or not all(isinstance(t, str) and t for t in types):
        raise SubscriptionError(f"{sub_id}: 'event_types' must be a non-empty list of strings")
    return Subscription(sub_id, url, secret, tuple(types))


def parse_subscriptions(raw: Any) -> list[Subscription]:
    if not isinstance(raw, list):
        raise SubscriptionError("subscriptions file must contain a JSON array")
    subs = [_parse_one(i, item) for i, item in enumerate(raw)]
    seen: set[str] = set()
    for sub in subs:
        if sub.id in seen:
            raise SubscriptionError(f"duplicate subscription id {sub.id!r}")
        seen.add(sub.id)
    return subs


def load_subscriptions(path: Path | str) -> list[Subscription]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SubscriptionError(f"cannot read {path}: {exc}") from exc
    return parse_subscriptions(raw)
