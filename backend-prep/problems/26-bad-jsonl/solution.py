"""26. Salvage a messy JSONL log: reference solution."""

import json
import re

ALIASES = ("user_id", "userId", "uid")


def _clean(payload: str) -> dict | str:  # the cleaned record, or an error reason
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return "invalid_json"
    if not isinstance(obj, dict):
        return "not_object"
    ids = [obj[k] for k in ALIASES if obj.get(k) is not None]
    if not ids:
        return "missing_user_id"
    if not all(type(v) is int or (isinstance(v, str) and v.strip()) for v in ids):
        return "invalid_user_id"
    ids = {v.strip() if isinstance(v, str) else str(v) for v in ids}
    if len(ids) > 1:
        return "conflicting_user_id"
    score = obj.get("score")
    if score is not None:
        s = str(score).strip()  # bools, lists and dicts stringify to something float() rejects
        try:
            score = float(s[:-1]) / 100 if s.endswith("%") else float(s)
        except ValueError:
            return "invalid_score"
        if not 0 <= score <= 1:  # also false for nan
            return "invalid_score"
    rest = {k: v for k, v in obj.items() if k not in ALIASES and k != "score"}
    return {"user_id": ids.pop(), **rest, "score": score}


def parse_jsonl(text: str) -> tuple[list[dict], list[dict]]:
    records, errors = [], []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line_no, line = i + 1, lines[i].strip()
        i += 1
        if not line:
            continue
        if re.fullmatch(r"```(json)?", line, re.I):
            end = next((j for j in range(i, len(lines)) if lines[j].strip() == "```"), None)
            if end is None:
                errors.append({"line": line_no, "reason": "unclosed_fence"})
                break
            payload, i = "\n".join(lines[i:end]), end + 1
        else:
            m = re.fullmatch(r"```(?:json)?(.*)```", line, re.I | re.S)
            payload = m.group(1) if m else line
        result = _clean(payload)
        if isinstance(result, str):
            errors.append({"line": line_no, "reason": result})
        else:
            records.append(result)
    return records, errors


if __name__ == "__main__":
    from problem_api import sample_text

    records, errors = parse_jsonl(sample_text())
    print(*records, *errors, sep="\n")
