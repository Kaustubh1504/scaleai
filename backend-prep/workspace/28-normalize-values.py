"""28. Normalize messy field values

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping

MISSING_MARKERS = frozenset({"", "n/a", "na", "null", "none", "nan", "-"})
TRUE_WORDS = frozenset({"true", "t", "yes", "y", "1", "on"})
FALSE_WORDS = frozenset({"false", "f", "no", "n", "0", "off"})


def parse_missing(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, str):
        s = v.strip()
        return None if s.lower() in MISSING_MARKERS else s
    return v


def parse_number(v: Any) -> Decimal | None:
  
    v = v.strip()
    v = v.replace(",","")
    v = v.replace("$","")
    v = v.replace("(","")
    v = v.replace(")","")
    
    
    if v.isdigit():
        return Decimal(v)
    
    
    
        


def parse_bool(v: Any) -> bool | None:
    raise NotImplementedError


def split_multi(v: Any) -> list[str]:
    raise NotImplementedError


def normalize_id(v: Any) -> str | None:
    raise NotImplementedError


def normalize_category(v: Any, mapping: Mapping[str, Iterable[str]]) -> str | None:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import LABEL_MAPPING, SAMPLE_ROWS

    cleaners = {
        "task_id": normalize_id,
        "reward": parse_number,
        "qa_passed": parse_bool,
        "tags": split_multi,
        "label": lambda v: normalize_category(v, LABEL_MAPPING),
    }
    for row in SAMPLE_ROWS:
        out = {}
        for field, clean in cleaners.items():
            try:
                out[field] = clean(row[field])
            except ValueError as exc:
                out[field] = f"<error: {exc}>"
        print(out)
