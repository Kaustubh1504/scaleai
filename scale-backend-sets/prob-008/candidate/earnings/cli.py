"""Command line entry point: compute a pay period and write it as CSV."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

from earnings.calc import compute_earnings
from earnings.client import ApiError, EarningsClient
from mock_services.clock import RealClock


def parse_day(value: str) -> datetime:
    """'2024-04-01' -> 2024-04-01T00:00:00Z."""
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as fh:
        if not rows:
            return
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None, *, http: httpx.Client | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute annotator earnings for a pay period.")
    parser.add_argument("--base-url", default="http://127.0.0.1:9300")
    parser.add_argument("--client-id", default=os.environ.get("PLATFORM_CLIENT_ID", "finance"))
    parser.add_argument("--client-secret", default=os.environ.get("PLATFORM_CLIENT_SECRET", "finance-secret"))
    parser.add_argument("--start", required=True, type=parse_day, help="first day of the period (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, type=parse_day, help="day after the period (YYYY-MM-DD)")
    parser.add_argument("--out", type=Path, default=Path("earnings.csv"))
    args = parser.parse_args(argv)

    http = http or httpx.Client(base_url=args.base_url)
    client = EarningsClient(http, args.client_id, args.client_secret, RealClock())
    try:
        report = compute_earnings(client, args.start, args.end)
    except ApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    write_csv(args.out, report["annotators"])
    print(f"wrote {args.out}: {report['totals']}")
    return 0
