"""Majority vote over the submissions of one task."""

from __future__ import annotations

from collections import Counter
from typing import NamedTuple


class Outcome(NamedTuple):
    state: str
    consensus_label: str | None
    agreement: float | None


def decide(labels: list[str], redundancy: int) -> Outcome:
    """Final state for a task that has received ``redundancy`` submissions."""
    if redundancy == 1:
        return Outcome("submitted", None, None)
    label, votes = Counter(labels).most_common(1)[0]
    agreement = round(votes / redundancy, 2)
    if votes * 2 > redundancy:
        return Outcome("completed", label, agreement)
    return Outcome("disputed", None, agreement)
