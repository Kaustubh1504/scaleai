"""18. Nested JSON with gaps: reference solution."""

from __future__ import annotations

from typing import Any, Callable


def get_path(obj: Any, path: str, default: Any = None) -> Any:
    if path == "":
        return obj
    for seg in path.split("."):
        if isinstance(obj, dict) and seg in obj:
            obj = obj[seg]
        elif isinstance(obj, list) and seg.isdigit() and int(seg) < len(obj):
            obj = obj[int(seg)]
        else:
            return default
    return obj


# Converters return None when the value counts as blank.
def _clean(v: Any) -> str | None:
    return v.strip() if isinstance(v, str) and v.strip().lower() not in ("", "null") else None


def _to_id(v: Any) -> str | None:
    return str(v) if type(v) is int else _clean(v)


def _to_skills(v: Any) -> list[str] | None:
    if isinstance(v, str):
        v = v.split(",")
    if not isinstance(v, list):
        return None
    return [s for s in map(_clean, v) if s] or None


def _to_rating(v: Any) -> float | None:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    try:
        return float(_clean(v))
    except (TypeError, ValueError):
        return None


def _to_active(v: Any) -> bool | None:
    if isinstance(v, bool):
        return v
    return {"true": True, "false": False}.get((_clean(v) or "").lower())


def _first(record: dict, paths: tuple[str, ...], convert: Callable[[Any], Any]) -> Any:
    for p in paths:
        value = convert(get_path(record, p))
        if value is not None:
            return value
    return None


def to_profile(record: dict) -> dict:
    pid = _first(record, ("id", "annotator_id"), _to_id)
    if pid is None:
        raise ValueError(f"record has no usable id: {record!r}"[:200])
    parts = [_clean(get_path(record, p)) for p in ("profile.first_name", "profile.last_name")]
    email = _first(record, ("email", "contact.email"), _clean)
    country = _first(record, ("country", "address.country", "addresses.0.country"), _clean)
    active = _first(record, ("active",), _to_active)
    if active is None:
        active = (_clean(record.get("status")) or "").lower() == "active"
    return {
        "id": pid,
        "name": _first(record, ("name", "profile.full_name"), _clean)
                or " ".join(filter(None, parts)) or None,
        "email": email and email.lower(),
        "country": country and country.upper(),
        "city": _first(record, ("city", "address.city", "addresses.0.city"), _clean),
        "skills": _first(record, ("skills", "profile.skills"), _to_skills) or [],
        "rating": _first(record, ("rating", "stats.rating"), _to_rating),
        "active": active,
    }


if __name__ == "__main__":
    from problem_api import RECORDS

    for rec in RECORDS:
        print(to_profile(rec))
