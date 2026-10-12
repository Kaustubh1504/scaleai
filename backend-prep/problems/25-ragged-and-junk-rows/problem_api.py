"""Sample file for problem 25. Paths are absolute (the judge runs in a temp dir)."""

from __future__ import annotations

from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

# Two payout exports concatenated with `cat`: comments, a repeated header,
# TOTAL / "Exported N rows" footers, ragged rows and multi-line quoted notes.
PAYOUTS = DATA / "annotator_payouts.csv"
REQUIRED = ["annotator_id", "amount_usd"]
