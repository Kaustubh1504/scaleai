"""Publish a computed pay period to the results sink, safely (PART3.md)."""

from __future__ import annotations

import logging

from earnings.client import ApiError, AuthError, EarningsClient

log = logging.getLogger(__name__)


def payout_key(period: str, annotator_id: str) -> str:
    return f"payout:{period}:{annotator_id}"


def publish_payouts(client: EarningsClient, report: dict) -> dict:
    """POST one payout per payable annotator. Safe to re-run: the idempotency key
    makes a repeat a replay, not a second payment. One failure does not stop the rest."""
    published: list[str] = []
    failed: list[str] = []
    for row in report["annotators"]:
        if row.get("on_hold") or row["earnings_cents"] <= 0:
            continue
        annotator_id = row["annotator_id"]
        body = {"annotator_id": annotator_id, "period": report["period"], "amount_cents": row["earnings_cents"]}
        try:
            client.post("/v1/results", body, idempotency_key=payout_key(report["period"], annotator_id))
        except AuthError:
            raise
        except ApiError as exc:
            log.warning("payout for %s failed: %s", annotator_id, exc)
            failed.append(annotator_id)
        else:
            published.append(annotator_id)
    return {"published": published, "failed": failed}
