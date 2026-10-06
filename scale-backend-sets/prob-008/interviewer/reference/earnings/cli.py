"""Command line entry point: compute a pay period, write it as CSV, optionally publish it."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

from earnings.calc import compute_earnings
from earnings.client import ApiError, EarningsClient
from earnings.normalize import DataError
from earnings.payouts import publish_payouts
from mock_services.clock import RealClock

COLUMNS = ["annotator_id", "handle", "approved", "rejected", "pending", "earnings_cents", "gold_bonus_cents",
           "on_hold"]


def parse_day(value: str) -> datetime:
    """'2024-04-01' -> 2024-04-01T00:00:00Z; a full ISO-8601 time is accepted too (naive = UTC)."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def write_csv(path: Path, rows: list[dict]) -> None:
    """Atomic: readers never see a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None, *, http: httpx.Client | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute annotator earnings for a pay period.")
    parser.add_argument("--base-url", default="http://127.0.0.1:9300")
    parser.add_argument("--client-id", default=os.environ.get("PLATFORM_CLIENT_ID", "finance"))
    parser.add_argument("--client-secret", default=os.environ.get("PLATFORM_CLIENT_SECRET", "finance-secret"))
    parser.add_argument("--start", required=True, type=parse_day, help="period start, inclusive (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, type=parse_day, help="period end, exclusive (YYYY-MM-DD)")
    parser.add_argument("--out", type=Path, default=Path("earnings.csv"))
    parser.add_argument("--publish", action="store_true", help="POST payable amounts to /v1/results")
    args = parser.parse_args(argv)

    http = http or httpx.Client(base_url=args.base_url)
    client = EarningsClient(http, args.client_id, args.client_secret, RealClock())
    try:
        report = compute_earnings(client, args.start, args.end)
    except (ApiError, DataError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    write_csv(args.out, report["annotators"])
    print(f"wrote {args.out}: {json.dumps(report['totals'])}")
    if report["unknown_reward_task_ids"]:
        print(f"unknown reward (excluded): {', '.join(report['unknown_reward_task_ids'])}")
    if not args.publish:
        return 0
    try:
        outcome = publish_payouts(client, report)
    except ApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"published {len(outcome['published'])} payouts; failed: {outcome['failed'] or 'none'}")
    return 1 if outcome["failed"] else 0
