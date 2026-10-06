import json
import re

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
FRACTION = re.compile(r"(?:score|rating)\s*[:=]\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
VERDICT = re.compile(r"verdict\s*[:=]\s*(pass|fail)\b", re.IGNORECASE)
DEFAULT_SCALE = 10


def _json_object(text):
    match = FENCE.search(text)
    body = match.group(1) if match else text
    start, end = body.find("{"), body.rfind("}")
    if start == -1 or end < start:
        return None
    try:
        obj = json.loads(body[start:end + 1])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


# VERIFIED
def extract_fraction(text):
    """'Score: 7/10' or 'rating = 4.5 / 5' -> (7.0, 10.0); None when there is no such phrase."""
    match = FRACTION.search(text)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def normalised_score(text):
    """Judge output -> score in [0, 1], or None when it cannot be read."""
    obj = _json_object(text)
    if obj is not None and "score" in obj:
        try:
            num, den = float(obj["score"]), float(obj.get("scale", DEFAULT_SCALE))
        except (TypeError, ValueError):
            return None
    elif (fraction := extract_fraction(text)) is not None:
        num, den = fraction
    elif (verdict := VERDICT.search(text)) is not None:
        return 1.0 if verdict.group(1).lower() == "pass" else 0.0
    else:
        return None
    if den <= 0 or not 0 <= num <= den:
        return None
    return num / den
