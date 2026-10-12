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


def parse_jsonl(text: str) -> tuple[list[dict], list[dict]]:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import sample_text

    records, errors = parse_jsonl(sample_text())
    for r in records:
        print(r)
    for e in errors:
        print("  line", e["line"], e["reason"])
