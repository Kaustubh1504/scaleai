"""28. Normalize messy field values: reference solution."""

import math
import re
from decimal import Decimal
from typing import Any

MISSING = {"", "n/a", "na", "null", "none", "nan", "-"}
TRUE_WORDS = {"true", "t", "yes", "y", "1", "on"}
FALSE_WORDS = {"false", "f", "no", "n", "0", "off"}
# optional $, then grouped thousands | plain/scientific | .5, then optional %
NUMBER = re.compile(r"(\$?)(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|\.\d+)(%?)")


def parse_missing(v: Any) -> Any:
    if isinstance(v, str):
        v = v.strip()
        return None if v.lower() in MISSING else v
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return v


def parse_number(v: Any) -> Decimal | None:
    v = parse_missing(v)
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (str, int, float, Decimal)):
        raise ValueError(f"not a number: {v!r}")
    if not isinstance(v, str):
        d = Decimal(str(v))  # via str() so 0.1 stays 0.1, not the exact binary float
        if not d.is_finite():
            raise ValueError(f"not a finite number: {v!r}")
        return d
    s, negative = v, False
    if s.startswith("(") and s.endswith(")"):
        s, negative = s[1:-1].strip(), True
    elif s.startswith(("+", "-")):
        s, negative = s[1:], s[0] == "-"
    m = NUMBER.fullmatch(s)
    if not m or (m[1] and m[3]):
        raise ValueError(f"not a number: {v!r}")
    d = Decimal(m[2].replace(",", ""))
    if m[3]:
        d /= 100
    return -d if negative else d


def parse_bool(v: Any) -> bool | None:
    v = parse_missing(v)
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, (str, int)):
        word = str(v).lower()
        if word in TRUE_WORDS:
            return True
        if word in FALSE_WORDS:
            return False
    raise ValueError(f"not a boolean: {v!r}")


def split_multi(v: Any) -> list[str]:
    v = parse_missing(v)
    if v is None:
        return []
    chunks = [v] if isinstance(v, str) else v
    parts = (p.strip() for chunk in chunks for p in re.split(r"[;|,]", chunk))
    return list(dict.fromkeys(p for p in parts if p))


def normalize_id(v: Any) -> str | None:
    v = parse_missing(v)
    if v is None:
        return None
    if isinstance(v, str) and re.fullmatch(r"[A-Z0-9_-]+", v.upper()):
        return v.upper()
    if type(v) is int and v >= 0:
        return str(v)
    raise ValueError(f"bad id: {v!r}")  # includes floats: 7.0 has already lost its leading zeros


def _key(s: str) -> str:
    return " ".join(s.lower().replace("_", " ").replace("-", " ").split())


def normalize_category(v: Any, mapping: dict[str, list[str]]) -> str | None:
    lookup = {}
    for canonical, synonyms in mapping.items():
        for name in (canonical, *synonyms):
            if lookup.setdefault(_key(name), canonical) != canonical:
                raise ValueError(f"ambiguous mapping: {name!r}")
    v = parse_missing(v)
    if v is None:
        return None
    if not isinstance(v, str) or _key(v) not in lookup:
        raise ValueError(f"unknown category: {v!r}")
    return lookup[_key(v)]


if __name__ == "__main__":
    from problem_api import LABEL_MAPPING, SAMPLE_ROWS

    for row in SAMPLE_ROWS:
        for field, clean in [("task_id", normalize_id), ("reward", parse_number),
                             ("qa_passed", parse_bool), ("tags", split_multi)]:
            try:
                print(field, repr(clean(row[field])), end="  ")
            except ValueError as exc:
                print(field, "<error>", exc, end="  ")
        print()
