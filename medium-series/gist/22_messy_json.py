# 22. Normalize messy JSON (paths, blanks, numbers, booleans, dates)
# Standalone: copy this file as-is. Deps: stdlib

import re
from datetime import datetime, timezone

MISSING = {"", "null", "none", "n/a", "na", "-"}


def get_path(obj, path: str, default=None):
    """get_path(rec, "user.profile.email") or "items.0.id". Returns default if any step is missing."""
    for part in path.split("."):
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        elif isinstance(obj, list) and part.lstrip("-").isdigit() and -len(obj) <= int(part) < len(obj):
            obj = obj[int(part)]
        else:
            return default
    return obj


def clean_str(v):
    """Stripped string, or None for None / "" / "null" / "N/A" / "-"."""
    if v is None:
        return None
    s = str(v).strip()
    return None if s.lower() in MISSING else s


def first(record, *paths, convert=clean_str):
    """First path whose converted value isn't None: first(rec, "email", "contact.email")."""
    for p in paths:
        v = convert(get_path(record, p))
        if v is not None:
            return v
    return None


def to_number(v):
    """12, "12", " $1,234.50 ", "1e3" -> int/float. bools, junk, NaN, inf -> None."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        n = v
    else:
        s = re.sub(r"[,\s$€£]", "", str(v))
        try:
            n = int(s)
        except ValueError:
            try:
                n = float(s)
            except ValueError:
                return None
    if isinstance(n, float) and (n != n or n in (float("inf"), float("-inf"))):
        return None
    return n


def to_bool(v):
    """True/False from bools, 0/1, "yes"/"no", "t"/"f"... None if unclear."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    s = str(v).strip().lower() if v is not None else ""
    if s in ("true", "t", "yes", "y", "1"):
        return True
    if s in ("false", "f", "no", "n", "0"):
        return False
    return None


def to_datetime(v):
    """ISO strings (with Z or offset), dates, epoch seconds or milliseconds -> aware UTC datetime, else None."""
    if v is None or isinstance(v, bool):
        return None
    s = str(v).strip()
    if isinstance(v, (int, float)) or re.fullmatch(r"\d{9,13}(\.\d+)?", s):
        ts = float(s)
        if ts > 1e11:                                     # milliseconds
            ts /= 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
