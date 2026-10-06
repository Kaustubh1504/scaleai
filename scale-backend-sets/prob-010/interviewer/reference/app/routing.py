"""Where a classified document goes: auto-accepted, or the human review queue."""

from __future__ import annotations

from dataclasses import dataclass

from app.classifier import Classification

INGESTED, AUTO_ACCEPTED, NEEDS_REVIEW, REVIEWED = "ingested", "auto_accepted", "needs_review", "reviewed"


@dataclass(frozen=True)
class Route:
    status: str
    final_label: str | None
    review_reason: str | None


def route(result: Classification, threshold: float) -> Route:
    """A pure function of the classification, so the rule is testable without a database."""
    if not result.ok:
        return Route(NEEDS_REVIEW, None, "classification_failed")
    if not result.agreed:
        return Route(NEEDS_REVIEW, None, "disagreement")
    if result.confidence >= threshold:
        return Route(AUTO_ACCEPTED, result.label, None)
    return Route(NEEDS_REVIEW, None, "low_confidence")
