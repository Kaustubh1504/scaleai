"""30. Integrity checks across entities

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import math
from datetime import datetime
from typing import Any, NamedTuple

ANNOTATOR_STATUSES = {"active", "suspended", "offboarded"}
TASK_STATUSES = {"open", "in_progress", "completed", "cancelled"}
SUBMISSION_STATUSES = {"pending", "accepted", "rejected"}


class Violation(NamedTuple):
    entity: str  # "annotator" | "task" | "submission"
    id: str
    rule: str
    detail: str


def parse_instant(value: Any) -> datetime | None:
    """An aware datetime for an ISO 8601 string with Z or an offset; None for anything else."""
    raise NotImplementedError


def check(dataset: dict) -> list[Violation]:
    raise NotImplementedError


if __name__ == "__main__":
    from collections import Counter

    from problem_api import load_dataset

    violations = check(load_dataset())
    for v in violations:
        print(f"{v.entity:<10} {v.id:<4} {v.rule:<30} {v.detail}")
    print(Counter(v.rule for v in violations))
