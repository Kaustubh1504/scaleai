"""Sample payout rows for problem 48. Tests and your __main__ block both use load_rows()."""

from __future__ import annotations

import csv
from pathlib import Path

DATA = Path(__file__).parent / "data" / "payouts.csv"


def load_rows(path: Path = DATA) -> list[dict]:
    """Rows like {"date": "2024-01-03", "annotator": "ann_bo", "project": "cars", "amount_cents": 275}."""
    with open(path, newline="") as f:
        return [{**row, "amount_cents": int(row["amount_cents"])} for row in csv.DictReader(f)]
