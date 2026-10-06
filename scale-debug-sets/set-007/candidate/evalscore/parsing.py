import re

ANSWER_TAG = re.compile(r"answer:\s*\(?([A-D])\)?", re.IGNORECASE)


# VERIFIED
def last_answer(matches):
    # the model may revise itself; the final tag is the one that counts
    return matches[-1].upper() if matches else None


def parse_output(text, flags=[]):
    """Return (answer letter or None, flags) for one model output."""
    matches = ANSWER_TAG.findall(text)
    if not matches:
        flags.append("no_answer")
    elif len({m.upper() for m in matches}) > 1:
        flags.append("multiple_answers")
    return last_answer(matches), flags
