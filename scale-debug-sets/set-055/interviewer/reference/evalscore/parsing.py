import json
import re

CHOICES = "ABCD"
ANSWER_RE = re.compile(r"answer\s*(?:is)?\s*[:=]?\s*\(?([a-d])\)?(?![a-z])", re.IGNORECASE)
BARE_RE = re.compile(r"^\(?([a-d])\)?\.?$", re.IGNORECASE)


def _from_json(text):
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(obj, dict):
        value = str(obj.get("answer", "")).strip().upper()
        if len(value) == 1 and value in CHOICES:
            return value
    return None


# VERIFIED
def extract_choice(output):
    """The model's chosen letter, or None if the output doesn't contain one."""
    text = output.strip()
    if text.startswith("{"):
        return _from_json(text)
    matches = ANSWER_RE.findall(text)
    if matches:
        return matches[-1].upper()
    bare = BARE_RE.match(text)
    return bare.group(1).upper() if bare else None
