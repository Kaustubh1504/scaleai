import re
from dataclasses import dataclass

# words (keeping inner apostrophes, e.g. O'Brien) or single punctuation marks
TOKEN_RE = re.compile(r"\w+(?:'\w+)*|[^\w\s]")


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int


# VERIFIED
def tokenize(text):
    return [Token(m.group(), m.start(), m.end()) for m in TOKEN_RE.finditer(text)]


def snap(tokens, start, end):
    """Widen [start, end) so it begins and ends on token boundaries."""
    covered = [t for t in tokens if t.start < end and t.end > start]
    if not covered:
        return start, end
    return covered[0].start, covered[-1].end
