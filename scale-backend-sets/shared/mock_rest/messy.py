"""Deterministic field-level inconsistency, the way real third-party APIs look.

Each variant maps a canonical value to how it appears on the wire. A variant
that does not apply to the value's type leaves it unchanged.
"""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timezone
from typing import Any, Callable

from .config import FieldMess

DROP = object()  # remove the key entirely


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _as_str(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return value


def _epoch(value: Any, scale: int) -> Any:
    parsed = _parse_iso(value)
    return int(parsed.timestamp() * scale) if parsed else value


def _iso_naive(value: Any) -> Any:
    parsed = _parse_iso(value)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None).isoformat() if parsed else value


def _iso_offset(value: Any) -> Any:
    parsed = _parse_iso(value)
    return parsed.astimezone(timezone.utc).isoformat() if parsed else value  # "+00:00" instead of "Z"


VARIANTS: dict[str, Callable[[Any], Any]] = {
    "null": lambda v: None,
    "missing": lambda v: DROP,
    "str": _as_str,
    "float": lambda v: float(v) if isinstance(v, int) and not isinstance(v, bool) else v,
    "epoch": lambda v: _epoch(v, 1),
    "epoch_ms": lambda v: _epoch(v, 1000),
    "iso_naive": _iso_naive,
    "iso_offset": _iso_offset,
    "csv": lambda v: ",".join(str(x) for x in v) if isinstance(v, list) else v,
    "bool_int": lambda v: int(v) if isinstance(v, bool) else v,
    "bool_str": lambda v: ("true" if v else "false") if isinstance(v, bool) else v,
    "upper": lambda v: v.upper() if isinstance(v, str) else v,
    "lower": lambda v: v.lower() if isinstance(v, str) else v,
    "padded": lambda v: f"  {v} " if isinstance(v, str) else v,
    "empty_str": lambda v: "" if isinstance(v, str) else v,
    "wrap": lambda v: {"value": v},
    "list": lambda v: v if isinstance(v, list) else [v],
}


def _fraction(*parts: object) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(digest[:8], 16) / 0x1_0000_0000


def _apply(node: Any, keys: list[str], transform: Callable[[Any], Any]) -> None:
    if not keys or not isinstance(node, dict):
        return
    head, rest = keys[0], keys[1:]
    is_list = head.endswith("[]")
    key = head[:-2] if is_list else head
    if key not in node:
        return
    if is_list:
        if isinstance(node[key], list):
            for i, item in enumerate(node[key]):
                if rest:
                    _apply(item, rest, transform)
                else:
                    node[key][i] = transform(item)
        return
    if rest:
        _apply(node[key], rest, transform)
        return
    new = transform(node[key])
    if new is DROP:
        del node[key]
    else:
        node[key] = new


def render(record: dict, rules: list[FieldMess], *, seed: int, resource: str, record_id: Any) -> dict:
    """The record as the API serves it. Never mutates ``record``."""
    out = copy.deepcopy(record)
    for rule in rules:
        if _fraction(seed, resource, record_id, rule.path, "hit") >= rule.rate or not rule.variants:
            continue
        pick = rule.variants[int(_fraction(seed, resource, record_id, rule.path, "pick") * len(rule.variants))]
        if pick not in VARIANTS:
            raise ValueError(f"unknown variant {pick!r}; expected one of {sorted(VARIANTS)}")
        _apply(out, rule.path.split("."), VARIANTS[pick])
    return out
