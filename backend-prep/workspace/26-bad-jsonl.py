"""26. Salvage a messy JSONL log

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import json
import math
import re
from typing import Any

USER_ID_ALIASES = ("user_id", "userId", "uid")
FENCE_OPEN = re.compile(r"```(json)?", re.IGNORECASE)
FENCE_ONE_LINE = re.compile(r"```(?:json)?(.*)```", re.IGNORECASE | re.DOTALL)

class _Invalid(Exception):
    """Internal: carries an error reason out of the normalizers."""

def extract(lines):
    out = []
    i = 0
    while i < len(lines):
        line_no = i + 1
        line = lines[i].strip()
        i += 1
        
        if not line:
            continue
        
        if FENCE_OPEN.fullmatch(line):
            body = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
                
            if i >= len(lines):
                out.append((line_no, None))
                break
                
            i += 1 
            out.append((line_no, "\n".join(body)))
            continue
        
        m = FENCE_ONE_LINE.fullmatch(line)
        out.append((line_no, m.group(1) if m else line))
    
    return out

def _user_id(obj: dict) -> str:
    present = [obj[k] for k in USER_ID_ALIASES if obj.get(k) is not None]
    if not present:
        raise _Invalid("missing_user_id")
    ids = set()
    for value in present:
        if isinstance(value, bool) or not isinstance(value, (str, int)) or (isinstance(value, str) and not value.strip()):
            raise _Invalid("invalid_user_id")
        ids.add(value.strip() if isinstance(value, str) else str(value))
    if len(ids) > 1:
        raise _Invalid("conflicting_user_id")
    return ids.pop()

def _score(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise _Invalid("invalid_score")
    try:
        if isinstance(value, (int, float)):
            score = float(value)
        elif isinstance(value, str):
            s = value.strip()
            score = float(s[:-1]) / 100 if s.endswith("%") else float(s)
        else:
            raise _Invalid("invalid_score")
    except ValueError:
        raise _Invalid("invalid_score") from None
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise _Invalid("invalid_score")
    return score

def normalize(obj):
    if not isinstance(obj, dict):
        raise _Invalid("not_object")
    
    user_id = _user_id(obj)
    score = _score(obj.get("score"))
    rest = {}
    for k, v in obj.items():
        if k not in USER_ID_ALIASES and k != "score":
            rest[k] = v
    
    return {"user_id":user_id, **rest, "score":score}

def parse_jsonl(text: str) -> tuple[list[dict], list[dict]]:
    records, errors = [],[]
    for line_no, payload in extract(text.splitlines()):
        try:
            if payload is None:
                raise _Invalid("unclosed_fence")
            
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                raise _Invalid("invalid_json")
                
            records.append(normalize(obj))
        
        except _Invalid as exc:
            errors.append({"line": line_no, "reason": str(exc)})
            
            
    
    return records, errors
                
            
        


if __name__ == "__main__":
    from problem_api import sample_text

    records, errors = parse_jsonl(sample_text())
    for r in records:
        print(r)
    for e in errors:
        print("  line", e["line"], e["reason"])
