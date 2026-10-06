"""The token counter used by every mock service.

Real tokenizers are model specific; the mocks use a simple deterministic rule
so candidates, reference solutions and tests all agree on counts:
one token per run of word characters and one per punctuation character.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"\w+|[^\w\s]")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text or "")


def count_tokens(text: str) -> int:
    return len(tokenize(text))
