import re

ANSWER_RE = re.compile(r"answer\s*[:=]?\s*\(?([A-D])(?![A-Za-z])", re.IGNORECASE)
BARE_RE = re.compile(r"\(?([A-D])\)?\.?", re.IGNORECASE)


# VERIFIED
def parse_choice(output):
    """Return the chosen letter (A-D) from a model output, or None."""
    text = (output or "").strip()
    matches = ANSWER_RE.findall(text)
    if matches:
        return matches[-1].upper()
    bare = BARE_RE.fullmatch(text)
    if bare:
        return bare.group(1).upper()
    return None
