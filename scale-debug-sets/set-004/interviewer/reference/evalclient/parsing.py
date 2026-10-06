import json
import re
from dataclasses import dataclass

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class Grade:
    score: float
    passed: bool


def extract_json(text):
    match = FENCE.search(text)
    if match:
        text = match.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def _as_bool(value):
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def parse_completion(body):
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    obj = extract_json(content)
    if not isinstance(obj, dict) or "score" not in obj or "passed" not in obj:
        return None
    score = float(obj["score"])
    if not 0 <= score <= 10:
        return None
    return Grade(score=score, passed=_as_bool(obj["passed"]))
